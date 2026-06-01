from pathlib import Path
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import logging
import re
import requests as _requests

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, Prefetch, Q, Sum
from django.http import FileResponse, Http404, HttpResponseRedirect, JsonResponse
from django.utils.http import urlencode
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from cart.models import Cart, CartItem, Order, OrderItem
from cart.order_tracking import order_timeline, orders_with_timelines
from core.recently_viewed import record_product_view, recently_viewed_products
from inventory.models import Category, Product, ProductImage, ProductReview
from pages.forms import ContactInquiryForm
from pages.models import ContactInquiry


logger = logging.getLogger(__name__)

AUTH_STAFF_LOGIN_TEMPLATE = 'core/auth_staff_login.html'

SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
DJANGO_IMAGE_SUFFIX_RE = re.compile(r'^(?P<stem>.+)_[A-Za-z0-9]{7}$')
SUPPORTED_CURRENCIES = ('USD', 'EUR', 'KES', 'UGX')
PAYMENT_METHODS = ('mtn', 'airtel', 'worldremit', 'pesapal')
FALLBACK_RATES = {
    'USD': Decimal('1'),
    'EUR': Decimal('0.92'),
    'KES': Decimal('129.50'),
    'UGX': Decimal('3820'),
}


STALE_EMPTY_CART_DAYS = 7

# Login brute-force throttling (per client IP, uses LocMem cache).
LOGIN_FAIL_WINDOW_SEC = 900
LOGIN_FAIL_MAX_ATTEMPTS = 8


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _login_rate_keys(request):
    ip = _client_ip(request)
    return f'login_fail_{ip}', f'login_lock_{ip}'


def _login_is_locked(request):
    _, lock_key = _login_rate_keys(request)
    return bool(cache.get(lock_key))


def _login_clear_attempts(request):
    fail_key, lock_key = _login_rate_keys(request)
    cache.delete(fail_key)
    cache.delete(lock_key)


def _login_register_failure(request):
    fail_key, lock_key = _login_rate_keys(request)
    n = cache.get(fail_key, 0) + 1
    cache.set(fail_key, n, LOGIN_FAIL_WINDOW_SEC)
    if n >= LOGIN_FAIL_MAX_ATTEMPTS:
        cache.set(lock_key, True, LOGIN_FAIL_WINDOW_SEC)
        return True
    return False


def _workspace_images_dir():
    return Path(settings.BASE_DIR).parent / 'images'


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _cleanup_stale_empty_guest_carts(active_session_key=None):
    cutoff = timezone.now() - timedelta(days=STALE_EMPTY_CART_DAYS)
    stale_carts = Cart.objects.filter(
        user__isnull=True,
        created_at__lt=cutoff,
        items__isnull=True,
    )

    if active_session_key:
        stale_carts = stale_carts.exclude(session_key=active_session_key)

    stale_carts.delete()


def _current_cart(request, create=False):
    active_session_key = request.session.session_key
    _cleanup_stale_empty_guest_carts(active_session_key=active_session_key)

    if request.user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(
                user=request.user,
                defaults={'session_key': request.session.session_key}
            )
            return cart
        return Cart.objects.filter(user=request.user).first()

    session_key = _ensure_session_key(request)
    if create:
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
        return cart
    return Cart.objects.filter(session_key=session_key, user=None).first()


def _merge_guest_cart_into_user(request, user, session_key=None):
    session_key = session_key or request.session.session_key
    if not session_key:
        return

    guest_cart = Cart.objects.filter(session_key=session_key, user=None).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user, defaults={'session_key': session_key})

    for guest_item in guest_cart.items.select_related('product'):
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            product=guest_item.product,
            size=guest_item.size,
            color=guest_item.color,
            defaults={'quantity': guest_item.quantity},
        )
        if not created:
            user_item.quantity += guest_item.quantity
            user_item.save()

    guest_cart.delete()


def _attach_guest_orders_to_user(request, user):
    session_key = request.session.session_key
    if not session_key:
        return
    Order.objects.filter(session_key=session_key, user__isnull=True).update(user=user)


def _normalize_phone(value):
    return re.sub(r'\D', '', value or '')


def _phone_matches(order_phone, submitted_phone):
    stored = _normalize_phone(order_phone)
    submitted = _normalize_phone(submitted_phone)
    if not stored or not submitted:
        return False
    if stored == submitted:
        return True
    tail = 9
    return stored.endswith(submitted[-tail:]) or submitted.endswith(stored[-tail:])


def _render_checkout_success(request, order, checkout_prefs, grand_total, instructions):
    order.timeline_steps = order_timeline(order)
    request.session['last_order_ref'] = order.order_ref
    request.session.modified = True
    return render(request, 'core/checkout_success.html', {
        'order': order,
        'currency': checkout_prefs['currency'] if checkout_prefs else order.currency,
        'grand_total_display': (
            _format_money(grand_total, checkout_prefs['currency'])
            if checkout_prefs and grand_total is not None
            else _format_money(_safe_decimal(order.total_amount, Decimal('0')), order.currency)
        ),
        'payment_method': checkout_prefs['payment_method'] if checkout_prefs else order.payment_method,
        'instructions': instructions,
    })


def _catalog_image_files():
    image_dir = _workspace_images_dir()
    if not image_dir.exists():
        return []

    files = [
        f for f in image_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _product_image_url(image_field):
    image_name = Path(str(image_field)).name
    return reverse('catalog_image', args=[image_name])


def _candidate_image_names(image_name):
    requested_name = Path(image_name).name
    candidates = [requested_name]

    stem = Path(requested_name).stem
    suffix = Path(requested_name).suffix
    match = DJANGO_IMAGE_SUFFIX_RE.match(stem)
    if match:
        candidates.append(f"{match.group('stem')}{suffix}")

    return candidates


def _normalize_key(value):
    return ''.join(char for char in value.lower() if char.isalnum())


def _display_name_from_stem(stem):
    text = stem.replace('_', ' ').replace('-', ' ').strip()
    if not text:
        return 'Catalog Item'
    return ' '.join(part.capitalize() for part in text.split())


def _catalog_fallback_description(product):
    name = (product.name or '').lower()

    color_keywords = {
        'black': 'black',
        'white': 'white',
        'ivory': 'ivory',
        'cream': 'cream',
        'navy': 'navy',
        'blue': 'blue',
        'teal': 'teal',
        'green': 'green',
        'emerald': 'emerald',
        'olive': 'olive',
        'purple': 'purple',
        'violet': 'violet',
        'lilac': 'lilac',
        'pink': 'pink',
        'blush': 'blush',
        'magenta': 'magenta',
        'fuchsia': 'fuchsia',
        'peach': 'peach',
        'yellow': 'yellow',
        'lemon': 'lemon',
        'mustard': 'mustard',
        'gold': 'gold',
        'orange': 'orange',
        'tan': 'tan',
        'camel': 'camel',
        'oatmeal': 'oatmeal',
        'grey': 'grey',
        'gray': 'gray',
        'burgundy': 'burgundy',
        'maroon': 'maroon',
        'red': 'red',
        'scarlet': 'scarlet',
        'rust': 'rust',
    }

    type_keywords = {
        'pantsuit': 'pantsuit',
        'suit': 'suit set',
        'blazer': 'blazer set',
        'waistcoat': 'waistcoat set',
        'dress': 'dress',
        'midi': 'midi dress',
        'mini': 'mini dress',
        'maxi': 'maxi dress',
        'gown': 'gown',
        'cocktail': 'cocktail look',
        'sheath': 'sheath silhouette',
        'wrap': 'wrap silhouette',
        'skirt': 'skirt set',
        'office': 'office-ready outfit',
    }

    vibe_phrases = [
        'made for polished daytime styling.',
        'ideal for elevated work-to-evening wear.',
        'crafted for confident, modern dressing.',
        'designed to stand out at special occasions.',
        'built for comfort with a refined finish.',
        'tailored for effortless, versatile outfits.',
    ]

    color = ''
    for keyword, label in color_keywords.items():
        if keyword in name:
            color = label
            break

    item_type = 'fashion piece'
    for keyword, label in type_keywords.items():
        if keyword in name:
            item_type = label
            break

    key = f'{product.name}:{product.id}'
    vibe = vibe_phrases[sum(ord(char) for char in key) % len(vibe_phrases)]

    if color:
        return f'A {color} {item_type} {vibe}'
    return f'A {item_type} {vibe}'


def _fallback_ai_description(name, category, color):
    category_label = (category or '').strip()
    color_label = (color or '').strip()

    details = []
    if color_label:
        details.append(color_label)
    if category_label and category_label.lower() != 'default':
        details.append(category_label)

    detail_text = ' '.join(details).strip()
    if detail_text:
        detail_text = f' in {detail_text}'

    description_en = (
        f'{name} is a polished Kistie Store piece{detail_text}, designed for confident everyday styling. '
        'It delivers a clean, elegant look that works well for both special occasions and refined day wear.'
    )
    description_lg = (
        f'{name} kye kintu kya misono okuva e Kistie Store{detail_text}, '
        'ekisaanira okwambalibwa buli lunaku n’endabika ennongoofu era ey’omulembe. '
        'Kisobola okwambalibwa ku mikolo oba ku mirimu egyetaaga okulabika obulungi.'
    )
    return {
        'description_en': description_en,
        'description_lg': description_lg,
        'source': 'fallback',
    }


def _recent_images(limit=3):
    """
    Images for home hero + About strip.

    Uses the same ProductImage records as catalog/inventory (under MEDIA_ROOT, typically
    ``media/products/…``). Falls back to loose files in ``kistie-store/images/`` when no
    product images exist (legacy seed flow).
    """
    qs = (
        ProductImage.objects.exclude(image='')
        .select_related('product')
        .order_by('-product__created_at', 'id')
    )

    paths = []
    seen_names = set()
    scan_cap = max(limit * 12, 48)
    for pi in qs[:scan_cap]:
        raw = str(pi.image).strip()
        if not raw:
            continue
        fname = Path(raw).name
        if not fname or fname in seen_names:
            continue
        seen_names.add(fname)
        paths.append(Path(fname))
        if len(paths) >= limit:
            break

    if paths:
        return paths[:limit]
    return _catalog_image_files()[:limit]


def _featured_products(limit=3):
    products = Product.objects.prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('id'))
    ).filter(stock_quantity__gt=0).order_by('-created_at')[:limit]

    featured = []
    for product in products:
        images = list(product.images.all())
        if not images:
            continue

        featured.append({
            'id': product.id,
            'slug': product.slug,
            'name': product.name,
            'description': (product.description or '').strip() or 'Curated premium fashion for confident everyday wear.',
            'price': _format_money(_safe_decimal(product.price, Decimal('0')), 'USD'),
            'image_url': _product_image_url(images[0].image),
            'sizes': product.size_list(),
        })
    return featured


def _safe_same_site_path(path):
    """Allow only relative same-site redirects (no open redirect)."""
    path = (path or '').strip()
    if path.startswith('/') and not path.startswith('//'):
        return path
    return ''


def _redirect_after_cart_action(request, product, *, success=False, error_message=''):
    next_path = _safe_same_site_path(request.POST.get('next'))
    if success:
        messages.success(request, f'Added {product.name} to your cart.')
        if next_path:
            return redirect(next_path)
        return redirect('cart')
    if error_message:
        messages.error(request, error_message)
    if next_path:
        return redirect(next_path)
    if product.slug:
        return redirect('product_detail', slug=product.slug)
    return redirect('shop')


def _safe_decimal(value, default):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _format_money(amount, currency):
    decimals = Decimal('1') if currency == 'UGX' else Decimal('0.01')
    rounded = amount.quantize(decimals, rounding=ROUND_HALF_UP)
    return f'{rounded:,.0f}' if currency == 'UGX' else f'{rounded:,.2f}'


def _parse_shop_price_filter(raw):
    """Parse shop GET filters price_min / price_max: strip commas, currency symbols; skip empty/infinity."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s in ('∞', '\u221e') or s.lower() in ('infinity', 'inf'):
        return None
    normalized = s.replace(',', '').replace('$', '').replace('\u00a0', '').strip()
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fetch_live_rates():
    url = 'https://api.frankfurter.app/latest?from=USD&to=EUR,KES,UGX'
    try:
        response = _requests.get(url, timeout=8)
        response.raise_for_status()
        payload = response.json()
        rates = {
            'USD': Decimal('1'),
            'EUR': _safe_decimal(payload.get('rates', {}).get('EUR'), FALLBACK_RATES['EUR']),
            'KES': _safe_decimal(payload.get('rates', {}).get('KES'), FALLBACK_RATES['KES']),
            'UGX': _safe_decimal(payload.get('rates', {}).get('UGX'), FALLBACK_RATES['UGX']),
        }
        return rates, payload.get('date', ''), 'live'
    except Exception as e:
        import sys
        print(f'Warning: Failed to fetch live exchange rates: {e}', file=sys.stderr)
        return FALLBACK_RATES, '', 'fallback'


def _checkout_preferences(request):
    currency = request.GET.get('currency') or request.session.get('currency') or 'USD'
    if currency not in SUPPORTED_CURRENCIES:
        currency = 'USD'
    request.session['currency'] = currency

    payment_method = request.GET.get('payment_method') or request.session.get('payment_method') or 'mtn'
    if payment_method not in PAYMENT_METHODS:
        payment_method = 'mtn'
    request.session['payment_method'] = payment_method

    rates, rates_updated, rates_source = _fetch_live_rates()
    rate = rates.get(currency, Decimal('1'))
    return {
        'currency': currency,
        'payment_method': payment_method,
        'rate': rate,
        'rates': rates,
        'rates_updated': rates_updated,
        'rates_source': rates_source,
    }


def _payment_instructions(country, payment_method):
    country_key = (country or '').strip().lower()
    business_name = 'Kistie_Store'
    mtn_number = '+256XXXXXXXXX'
    airtel_number = '+256XXXXXXXXX'

    if country_key == 'uganda':
        if payment_method == 'airtel':
            number_line = f'Number: {airtel_number} (Airtel)'
        elif payment_method == 'worldremit':
            number_line = 'Use WorldRemit and send to the business mobile money details provided.'
        else:
            number_line = f'Number: {mtn_number} (MTN)'

        return (
            'UGANDA PAYMENT INSTRUCTIONS\n\n'
            f'Send payment to: {business_name}\n'
            f'{number_line}\n\n'
            'After payment, send your transaction screenshot/reference to confirm your order.'
        )

    return (
        'INTERNATIONAL PAYMENT INSTRUCTIONS\n\n'
        'Use WorldRemit (or equivalent) with the details below:\n'
        f'Receiver Name: {business_name}\n'
        'Country: Uganda\n'
        f'Receiver Number: {mtn_number}\n'
        'Network: MTN or Airtel\n\n'
        'After transfer, send payment confirmation so we can verify and dispatch.'
    )


def _flash_contact_inquiry_success(request):
    backend = (getattr(settings, 'EMAIL_BACKEND', '') or '').lower()
    if 'console' in backend:
        messages.success(
            request,
            'Inquiry saved. Email preview was printed to the server console (console backend — not delivered to a real inbox).',
        )
    else:
        messages.success(request, 'Message sent. We received your inquiry and will follow up soon.')


def _flash_contact_inquiry_failure(request, exc):
    logger.exception('Failed to send contact inquiry email')
    if settings.DEBUG:
        detail = str(exc).strip()
        if len(detail) > 240:
            detail = detail[:237] + '...'
        suffix = f' ({detail})' if detail else ''
        messages.warning(
            request,
            'Inquiry saved, but email delivery failed.'
            f'{suffix} Check EMAIL_* in backend/.env and restart the Django server.',
        )
    else:
        messages.warning(
            request,
            'Inquiry saved, but email delivery failed. Please verify SMTP settings in production.'
        )


def _handle_contact_inquiry(request):
    if request.method != 'POST':
        return ContactInquiryForm(), False

    contact_form = ContactInquiryForm(request.POST)
    if not contact_form.is_valid():
        messages.error(request, 'Please correct the highlighted fields and try again.')
        return contact_form, False

    inquiry = ContactInquiry.objects.create(**contact_form.cleaned_data)
    try:
        send_mail(
            subject=f"New storefront inquiry: {inquiry.subject}",
            message=(
                f"Name: {inquiry.name}\n"
                f"Email: {inquiry.email}\n\n"
                f"Message:\n{inquiry.message}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
            fail_silently=False,
        )
        _flash_contact_inquiry_success(request)
    except Exception as exc:
        _flash_contact_inquiry_failure(request, exc)
    return contact_form, True


def health(request):
    wants_json = (
        request.GET.get('format') == 'json'
        or 'application/json' in (request.headers.get('Accept') or '')
    )
    if wants_json:
        return JsonResponse({'status': 'ok', 'service': 'kistie-store'}, status=200)
    return render(request, 'core/health.html', status=200)


def home(request):
    """Root URL opens the Shop storefront (canonical path ``/shop/``)."""
    return HttpResponseRedirect(reverse('shop'))


def contact(request):
    contact_form, sent = _handle_contact_inquiry(request)
    if sent:
        return redirect('contact')

    email_backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
    contact_email_console = email_backend == 'django.core.mail.backends.console.EmailBackend'
    return render(request, 'core/contact.html', {
        'contact_form': contact_form,
        'contact_email_console': contact_email_console,
    })


def about(request):
    brand_images = _recent_images(limit=2)
    return render(request, 'core/about.html', {'brand_images': brand_images})


def terms_of_service(request):
    return render(request, 'core/terms.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            pre_login_session_key = request.session.session_key
            user = form.save()
            login(request, user)
            _merge_guest_cart_into_user(request, user, session_key=pre_login_session_key)
            _attach_guest_orders_to_user(request, user)
            messages.success(request, 'Account created successfully. Welcome to Kistie Store.')
            return redirect('order_history')
        messages.error(request, 'Please correct the signup form and try again.')
    else:
        form = UserCreationForm()

    return render(request, 'core/auth_signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'GET' and _login_is_locked(request):
        messages.error(
            request,
            'Too many sign-in attempts from this address. Please wait a few minutes and try again.',
        )

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        if _login_is_locked(request):
            messages.error(
                request,
                'Too many sign-in attempts. Please try again in a few minutes.',
            )
            return render(request, 'core/auth_login.html', {'form': form})

        if form.is_valid():
            _login_clear_attempts(request)
            pre_login_session_key = request.session.session_key
            user = form.get_user()
            login(request, user)
            _merge_guest_cart_into_user(request, user, session_key=pre_login_session_key)
            _attach_guest_orders_to_user(request, user)
            messages.success(request, f'Welcome back, {user.username}.')
            return redirect('home')

        if _login_register_failure(request):
            messages.error(
                request,
                'Too many failed attempts. This address is temporarily limited. Try again later.',
            )
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core/auth_login.html', {'form': form})


def _staff_login_post(request, form):
    if _login_is_locked(request):
        messages.error(
            request,
            'Too many sign-in attempts. Please try again in a few minutes.',
        )
        return render(request, AUTH_STAFF_LOGIN_TEMPLATE, {'form': form})

    if not form.is_valid():
        if _login_register_failure(request):
            messages.error(
                request,
                'Too many failed attempts. This address is temporarily limited. Try again later.',
            )
        else:
            messages.error(request, 'Invalid username or password.')
        return None

    user = form.get_user()
    if not (user.is_superuser or user.has_perm('core.access_staff_dashboard')):
        messages.error(
            request,
            'This account does not have staff dashboard access. Ask your manager for the correct staff login.',
        )
        return render(request, AUTH_STAFF_LOGIN_TEMPLATE, {'form': AuthenticationForm(request)})

    _login_clear_attempts(request)
    pre_login_session_key = request.session.session_key
    login(request, user)
    _merge_guest_cart_into_user(request, user, session_key=pre_login_session_key)
    messages.success(request, f'Welcome, {user.username}.')
    return redirect('staff_dashboard')


def staff_login_view(request):
    """Dedicated entry for shop staff (permission ``access_staff_dashboard``); redirects to staff dashboard."""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.has_perm('core.access_staff_dashboard'):
            return redirect('staff_dashboard')
        messages.info(
            request,
            'You are already signed in with a shopper account. Staff dashboard requires staff access.',
        )
        return redirect('home')

    if request.method == 'GET' and _login_is_locked(request):
        messages.error(
            request,
            'Too many sign-in attempts from this address. Please wait a few minutes and try again.',
        )

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        response = _staff_login_post(request, form)
        if response is not None:
            return response

    return render(request, AUTH_STAFF_LOGIN_TEMPLATE, {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been signed out.')
    return redirect('home')


@login_required
def order_history(request):
    orders = orders_with_timelines(
        Order.objects.filter(user=request.user)
        .prefetch_related('items')
        .order_by('-created_at')
    )
    return render(request, 'core/order_history.html', {
        'orders': orders,
    })


def order_track(request):
    order = None
    form_order_ref = (request.GET.get('order_ref') or request.POST.get('order_ref') or '').strip().upper()
    form_phone = (request.POST.get('phone') or request.GET.get('phone') or '').strip()

    if not form_order_ref and request.session.get('last_order_ref'):
        form_order_ref = request.session['last_order_ref']

    if request.method == 'POST':
        order = Order.objects.filter(order_ref=form_order_ref).prefetch_related('items').first()
        if order and _phone_matches(order.phone, form_phone):
            order.timeline_steps = order_timeline(order)
        else:
            order = None
            messages.error(
                request,
                'We could not find an order with that reference and phone number. Check and try again.',
            )

    return render(request, 'core/order_track.html', {
        'order': order,
        'form_order_ref': form_order_ref,
        'form_phone': form_phone,
    })


@login_required
@permission_required('core.access_staff_dashboard', raise_exception=True)
def staff_dashboard(request):
    low_stock_threshold = 5
    order_counts = Order.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status=Order.STATUS_PENDING)),
        confirmed=Count('id', filter=Q(status=Order.STATUS_CONFIRMED)),
    )
    revenue_rows = (
        Order.objects.filter(status=Order.STATUS_CONFIRMED)
        .values('currency')
        .annotate(total=Sum('total_amount'))
        .order_by('currency')
    )
    low_stock_products = (
        Product.objects.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=low_stock_threshold,
        )
        .select_related('category')
        .order_by('stock_quantity', 'name')[:20]
    )
    recent_inquiries = ContactInquiry.objects.all()[:10]
    all_products = Product.objects.select_related('category').order_by('name')
    demand_forecasts = _compute_demand_forecasts()

    return render(request, 'core/staff_dashboard.html', {
        'order_counts': order_counts,
        'revenue_rows': revenue_rows,
        'low_stock_products': low_stock_products,
        'low_stock_threshold': low_stock_threshold,
        'recent_inquiries': recent_inquiries,
        'all_products': all_products,
        'demand_forecasts': demand_forecasts,
    })


def _compute_demand_forecasts():
    """
    Lightweight demand forecast: compute average daily sales per product
    from confirmed OrderItems, then estimate days until stock runs out.
    Returns a list of dicts sorted by urgency (fewest days first).
    """
    from datetime import timedelta
    from django.db.models import F

    # Look back 90 days of non-failed orders.
    # This keeps the dashboard useful when most orders are still pending payment.
    cutoff = timezone.now() - timedelta(days=90)
    rows = (
        OrderItem.objects
        .filter(order__created_at__gte=cutoff)
        .exclude(order__status=Order.STATUS_FAILED)
        .values('product_name')
        .annotate(total_sold=Sum('quantity'))
    )
    sold_map = {r['product_name']: r['total_sold'] for r in rows}

    forecasts = []
    for product in Product.objects.filter(stock_quantity__gt=0).select_related('category'):
        total_sold = sold_map.get(product.name, 0)
        if total_sold == 0:
            continue
        daily_rate = total_sold / 90.0
        days_left = int(product.stock_quantity / daily_rate)
        forecasts.append({
            'product': product,
            'daily_rate': round(daily_rate, 2),
            'days_left': days_left,
            'urgent': days_left <= 14,
        })

    forecasts.sort(key=lambda x: x['days_left'])
    return forecasts[:20]


@user_passes_test(lambda u: u.is_superuser)
def admin_audit_log(request):
    """Recent Django admin actions (LogEntry). Superusers only — staff use /staff/dashboard/."""
    entries = (
        LogEntry.objects.select_related('user', 'content_type')
        .order_by('-action_time')[:150]
    )
    return render(request, 'core/admin_audit_log.html', {
        'entries': entries,
    })


def _shop_filtered_products_queryset(request):
    category_raw = request.GET.get('category')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    size_q = (request.GET.get('size') or '').strip()
    search_q = (request.GET.get('q') or '').strip()

    products = (
        Product.objects.select_related('category')
        .annotate(
            review_avg=Avg(
                'reviews__rating',
                filter=Q(reviews__is_approved=True),
            ),
            review_count=Count(
                'reviews',
                filter=Q(reviews__is_approved=True),
            ),
        )
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('id'))
        )
    )

    if category_raw:
        try:
            cid = int(category_raw)
            products = products.filter(category_id=cid)
        except (TypeError, ValueError):
            pass

    parsed_min = _parse_shop_price_filter(price_min)
    if parsed_min is not None:
        products = products.filter(price_usd__gte=parsed_min)
    parsed_max = _parse_shop_price_filter(price_max)
    if parsed_max is not None:
        products = products.filter(price_usd__lte=parsed_max)

    if size_q:
        products = products.filter(sizes__icontains=size_q)

    search_parsed: dict = {}
    if search_q:
        from core.shop_search import search_hint_label, smart_shop_search

        products, search_parsed = smart_shop_search(products, search_q)
        if search_parsed.get('eu_size') and not size_q:
            size_q = search_parsed['eu_size']
        if search_parsed.get('max_price_usd') is not None and not parsed_max:
            parsed_max = search_parsed['max_price_usd']

    products = products.order_by('-created_at')

    filter_ctx = {
        'filter_category': category_raw or '',
        'filter_price_min': (price_min or '').strip(),
        'filter_price_max': (price_max or '').strip(),
        'filter_size': size_q,
        'filter_q': search_q,
        'search_hint': search_hint_label(search_parsed) if search_q else '',
    }
    return products, filter_ctx


def _shop_product_rows(products, checkout):
    rows = []
    for product in products:
        images = list(product.images.all())
        description = (product.description or '').strip()
        if description.lower() == 'auto-created from uploaded catalog image.':
            description = ''

        base_price = _safe_decimal(product.price, Decimal('0'))
        converted_price = base_price * checkout['rate']

        primary_url = _product_image_url(images[0].image) if images else ''
        detail_url = _product_image_url(images[1].image) if len(images) > 1 else primary_url

        review_label = ''
        review_count = getattr(product, 'review_count', None)
        review_avg = getattr(product, 'review_avg', None)
        if review_count and review_avg is not None:
            review_label = f'{review_avg:.1f} ★ ({review_count})'

        rows.append({
            'product': product,
            'price_display': _format_money(converted_price, checkout['currency']),
            'image_url': primary_url,
            'primary_url': primary_url,
            'detail_url': detail_url,
            'description': description or _catalog_fallback_description(product),
            'review_label': review_label,
            'category_name': product.category.name if product.category_id else '',
            'has_image': bool(images),
        })
    return rows


def _product_description_display(product):
    description = (product.description or '').strip()
    if description.lower() == 'auto-created from uploaded catalog image.':
        description = ''
    return description or _catalog_fallback_description(product)


def _product_image_gallery(product):
    gallery = []
    for img in product.images.all():
        gallery.append({
            'url': _product_image_url(img.image),
            'alt': img.alt_text or product.name,
        })
    return gallery


def _build_whatsapp_product_url(request, product, size=''):
    page_url = request.build_absolute_uri(product.get_absolute_url())
    lines = [
        "Hi Kistie Store! I'm interested in:",
        f'• {product.name} (SKU #{product.id})',
        f'• {page_url}',
    ]
    if size:
        lines.append(f'• EU size: {size}')
    text = '\n'.join(lines)
    return f'https://wa.me/256704757198?{urlencode({"text": text})}'


def _related_products_for_pdp(product, limit=4):
    """Same category first; fill with color/name similarity."""
    base_qs = (
        Product.objects.select_related('category')
        .exclude(pk=product.pk)
        .filter(stock_quantity__gt=0)
        .annotate(
            review_avg=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
        )
        .prefetch_related(Prefetch('images', queryset=ProductImage.objects.order_by('id')))
    )

    picked_ids = []
    rows = []

    if product.category_id:
        for p in base_qs.filter(category_id=product.category_id).order_by('-created_at')[:limit]:
            picked_ids.append(p.pk)
            rows.append(p)

    if len(rows) < limit and product.color:
        for p in (
            base_qs.filter(color__icontains=product.color)
            .exclude(pk__in=picked_ids)
            .order_by('-created_at')[: limit - len(rows)]
        ):
            picked_ids.append(p.pk)
            rows.append(p)

    if len(rows) < limit:
        name_tokens = [
            t.lower()
            for t in re.findall(r'[a-zA-Z]{4,}', product.name or '')
            if t.lower() not in ('with', 'dress', 'size', 'women')
        ][:4]
        similarity = Q()
        for token in name_tokens:
            similarity |= Q(name__icontains=token) | Q(description__icontains=token)
        if similarity:
            for p in (
                base_qs.filter(similarity)
                .exclude(pk__in=picked_ids)
                .order_by('-created_at')[: limit - len(rows)]
            ):
                picked_ids.append(p.pk)
                rows.append(p)

    if len(rows) < limit:
        for p in (
            base_qs.exclude(pk__in=picked_ids).order_by('-created_at')[: limit - len(rows)]
        ):
            rows.append(p)

    return rows


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category')
        .annotate(
            review_avg=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
        )
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('id')),
        ),
        slug=slug,
    )
    record_product_view(request, product.pk)

    try:
        checkout = _checkout_preferences(request)
    except Exception:
        logger.exception('product detail checkout prefs failed; using USD fallback')
        checkout = {
            'currency': 'USD',
            'rate': Decimal('1'),
            'payment_method': 'mtn',
            'rates_source': 'fallback',
            'rates_updated': '',
        }

    base_price = _safe_decimal(product.price_usd, Decimal('0'))
    converted_price = base_price * checkout['rate']
    old_price_display = ''
    if product.old_price and product.old_price > product.price_usd:
        old_converted = _safe_decimal(product.old_price, Decimal('0')) * checkout['rate']
        old_price_display = _format_money(old_converted, checkout['currency'])

    review_count = getattr(product, 'review_count', 0) or 0
    review_avg = getattr(product, 'review_avg', None)
    review_label = ''
    if review_count and review_avg is not None:
        review_label = f'{review_avg:.1f} ★ ({review_count})'

    related_rows = _shop_product_rows(
        _related_products_for_pdp(product),
        checkout,
    )
    recent_qs = recently_viewed_products(request, exclude_product_id=product.pk, limit=4)
    recent_rows = _shop_product_rows(recent_qs, checkout) if recent_qs else []

    description = _product_description_display(product)
    gallery = _product_image_gallery(product)
    canonical_url = request.build_absolute_uri(product.get_absolute_url())
    approved_reviews = list(
        ProductReview.objects.filter(product=product, is_approved=True)
        .select_related('user')
        .order_by('-created_at')[:12]
    )

    schema_images = []
    for item in gallery:
        schema_images.append(request.build_absolute_uri(item['url']))

    availability = 'https://schema.org/InStock' if product.stock_quantity > 0 else 'https://schema.org/OutOfStock'

    return render(request, 'core/product_detail.html', {
        'product': product,
        'description': description,
        'gallery': gallery,
        'price_display': _format_money(converted_price, checkout['currency']),
        'old_price_display': old_price_display,
        'currency': checkout['currency'],
        'review_label': review_label,
        'review_count': review_count,
        'review_avg': review_avg,
        'reviews': approved_reviews,
        'related_rows': related_rows,
        'recent_rows': recent_rows,
        'whatsapp_url': _build_whatsapp_product_url(request, product),
        'canonical_url': canonical_url,
        'schema_images': schema_images,
        'schema_price': str(converted_price.quantize(
            Decimal('1') if checkout['currency'] == 'UGX' else Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )),
        'schema_availability': availability,
        'category_name': product.category.name if product.category_id else '',
    })


def catalog(request):
    """Legacy ``/catalog/`` URL — redirects to Shop."""
    path = reverse('shop')
    qs = request.GET.urlencode()
    if qs:
        return HttpResponseRedirect(f'{path}?{qs}')
    return HttpResponseRedirect(path)


def legacy_inventory_redirect(request):
    """Legacy ``/inventory/`` storefront URL — redirects to canonical ``/shop/``."""
    path = reverse('shop')
    qs = request.GET.urlencode()
    if qs:
        return HttpResponseRedirect(f'{path}?{qs}')
    return HttpResponseRedirect(path)


def catalog_image(_request, image_name):
    requested_names = _candidate_image_names(image_name)

    # Try workspace image folder first (used by legacy catalog seed flow).
    workspace_dir = _workspace_images_dir().resolve()
    for requested_name in requested_names:
        workspace_candidate = (workspace_dir / requested_name).resolve()
        if workspace_dir in workspace_candidate.parents and workspace_candidate.exists() and workspace_candidate.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            return FileResponse(open(workspace_candidate, 'rb'))

    # Fallback to media folder where ProductImage files are stored on most deployments.
    media_root = Path(settings.MEDIA_ROOT).resolve()
    for requested_name in requested_names:
        media_candidate = (media_root / requested_name).resolve()
        if media_root in media_candidate.parents and media_candidate.exists() and media_candidate.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            return FileResponse(open(media_candidate, 'rb'))

    # Some files are nested (for example: media/products/products/<name>).
    for requested_name in requested_names:
        for candidate in media_root.rglob(requested_name):
            resolved = candidate.resolve()
            if media_root in resolved.parents and resolved.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                return FileResponse(open(resolved, 'rb'))

    raise Http404('Image not found.')


def _build_shop_page_context(request):
    checkout = _checkout_preferences(request)
    products, filter_ctx = _shop_filtered_products_queryset(request)
    shop_rows = _shop_product_rows(products, checkout)
    return {
        'shop_rows': shop_rows,
        'currency': checkout['currency'],
        'supported_currencies': SUPPORTED_CURRENCIES,
        'payment_method': checkout['payment_method'],
        'payment_methods': PAYMENT_METHODS,
        'rates_source': checkout['rates_source'],
        'rates_updated': checkout['rates_updated'],
        'rate_display': _format_money(checkout['rate'], checkout['currency']),
        'categories': Category.objects.all().order_by('name'),
        'total_items': len(shop_rows),
        **filter_ctx,
    }


def shop(request):
    """Single storefront (Shop page only): template ``core/shop.html``. No ``inventory.html`` / catalog HTML."""
    try:
        ctx = _build_shop_page_context(request)
    except Exception:
        logger.exception('shop page failed; using fallback rates')
        products, filter_ctx = _shop_filtered_products_queryset(request)
        fallback_checkout = {'currency': 'USD', 'rate': Decimal('1')}
        shop_rows = _shop_product_rows(products, fallback_checkout)
        ctx = {
            'shop_rows': shop_rows,
            'currency': 'USD',
            'supported_currencies': SUPPORTED_CURRENCIES,
            'payment_method': (
                pm if (pm := request.session.get('payment_method', 'mtn')) in PAYMENT_METHODS else 'mtn'
            ),
            'payment_methods': PAYMENT_METHODS,
            'rates_source': 'fallback',
            'rates_updated': '',
            'rate_display': '1.00',
            'categories': Category.objects.all().order_by('name'),
            'total_items': len(shop_rows),
            **filter_ctx,
        }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('core/_shop_results.html', ctx, request=request)
        return JsonResponse({
            'html': html,
            'total_items': ctx['total_items'],
            'search_hint': ctx.get('search_hint', ''),
        })

    return render(request, 'core/shop.html', ctx)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', '')
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    quantity = max(1, quantity)
    color = product.color
    available_sizes = product.size_list()

    if available_sizes and size not in available_sizes:
        return _redirect_after_cart_action(
            request,
            product,
            error_message='Please choose one of the listed EU sizes before adding this item to cart.',
        )

    if product.stock_quantity <= 0:
        return _redirect_after_cart_action(
            request,
            product,
            error_message='This item is currently out of stock.',
        )

    cart = _current_cart(request, create=True)
    item = CartItem.objects.filter(cart=cart, product=product, size=size, color=color).first()
    requested_quantity = quantity if item is None else item.quantity + quantity
    if requested_quantity > product.stock_quantity:
        return _redirect_after_cart_action(
            request,
            product,
            error_message=f'Only {product.stock_quantity} unit(s) available for {product.name}.',
        )

    if item is not None:
        item.quantity += quantity
    else:
        item = CartItem(cart=cart, product=product, size=size, color=color, quantity=quantity)

    item.save()
    return _redirect_after_cart_action(request, product, success=True)


def cart(request):
    try:
        checkout = _checkout_preferences(request)
        cart = _current_cart(request, create=False)
        items = []
        items_view = []
        grand_total = Decimal('0')

        if cart:
            items = cart.items.select_related('product')

        for item in items:
            base_price = _safe_decimal(item.product.price, Decimal('0'))
            line_total_base = base_price * item.quantity
            line_total = line_total_base * checkout['rate']
            grand_total += line_total
            items_view.append({
                'item': item,
                'price_display': _format_money(base_price * checkout['rate'], checkout['currency']),
                'line_total_display': _format_money(line_total, checkout['currency']),
            })

        return render(request, 'core/cart.html', {
            'cart': cart,
            'items': items,
            'items_view': items_view,
            'currency': checkout['currency'],
            'supported_currencies': SUPPORTED_CURRENCIES,
            'payment_method': checkout['payment_method'],
            'payment_methods': PAYMENT_METHODS,
            'grand_total_display': _format_money(grand_total, checkout['currency']),
            'rates_source': checkout['rates_source'],
            'rates_updated': checkout['rates_updated'],
            'rate_display': _format_money(checkout['rate'], checkout['currency']),
        })
    except Exception as e:
        import sys
        print(f'Error loading cart: {e}', file=sys.stderr)
        # Fall back to basic cart view with default currency
        cart = _current_cart(request, create=False)
        items = []
        items_view = []
        grand_total = Decimal('0')
        
        if cart:
            items = cart.items.select_related('product')
            for item in items:
                base_price = _safe_decimal(item.product.price, Decimal('0'))
                line_total = base_price * item.quantity
                grand_total += line_total
                items_view.append({
                    'item': item,
                    'price_display': str(base_price),
                    'line_total_display': str(line_total),
                })

        return render(request, 'core/cart.html', {
            'cart': cart,
            'items': items,
            'items_view': items_view,
            'currency': 'USD',
            'supported_currencies': SUPPORTED_CURRENCIES,
            'payment_method': 'mtn',
            'payment_methods': PAYMENT_METHODS,
            'grand_total_display': str(grand_total),
            'rates_source': 'fallback',
            'rates_updated': '',
            'rate_display': '1.00',
        })


def _validate_cart_stock(cart_items):
    for item in cart_items:
        product = item.product
        if product.stock_quantity <= 0:
            return f'{product.name} is out of stock. Please update your cart.'
        if item.quantity > product.stock_quantity:
            return f'{product.name} has only {product.stock_quantity} unit(s) available.'
    return ''


def _build_checkout_items_view(cart_items, checkout_prefs):
    items_view = []
    grand_total = Decimal('0')

    for item in cart_items:
        base_price = _safe_decimal(item.product.price, Decimal('0'))
        unit_price = base_price * checkout_prefs['rate']
        line_total = unit_price * item.quantity
        grand_total += line_total
        items_view.append({
            'name': item.product.name,
            'quantity': item.quantity,
            'size': item.size,
            'color': item.color,
            'unit_price_display': _format_money(unit_price, checkout_prefs['currency']),
            'line_total_display': _format_money(line_total, checkout_prefs['currency']),
        })

    return items_view, grand_total


def _lock_products_for_cart(cart_items):
    product_ids = [item.product_id for item in cart_items]
    locked_products = Product.objects.select_for_update().filter(id__in=product_ids)
    return {product.id: product for product in locked_products}


def _validate_locked_stock(cart_items, product_map):
    for item in cart_items:
        product = product_map.get(item.product_id)
        if product is None or product.stock_quantity <= 0:
            return f'{item.product.name} is now out of stock. Please review your cart.'
        if item.quantity > product.stock_quantity:
            return f'{item.product.name} now has only {product.stock_quantity} unit(s) left.'
    return ''


def _create_order_items_and_reduce_stock(order, cart_items, checkout_prefs, product_map):
    for item in cart_items:
        unit_price = (_safe_decimal(item.product.price, Decimal('0')) * checkout_prefs['rate']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_total = (unit_price * item.quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        OrderItem.objects.create(
            order=order,
            product_name=item.product.name,
            quantity=item.quantity,
            size=item.size,
            color=item.color,
            unit_price=unit_price,
            line_total=line_total,
        )

        product = product_map[item.product_id]
        product.stock_quantity -= item.quantity
        product.save(update_fields=['stock_quantity', 'updated_at'])


def _checkout_post(request, cart, cart_items, checkout_prefs, grand_total, context):
    form_data = {
        'name': (request.POST.get('name') or '').strip(),
        'email': (request.POST.get('email') or '').strip(),
        'phone': (request.POST.get('phone') or '').strip(),
        'country': (request.POST.get('country') or '').strip(),
        'notes': (request.POST.get('notes') or '').strip(),
    }
    context['form_data'] = form_data

    if not form_data['name'] or not form_data['phone'] or not form_data['country']:
        messages.error(request, 'Name, phone, and country are required to place your order.')
        return render(request, 'core/checkout.html', context)

    with transaction.atomic():
        product_map = _lock_products_for_cart(cart_items)
        locked_stock_error = _validate_locked_stock(cart_items, product_map)
        if locked_stock_error:
            messages.error(request, locked_stock_error)
            return redirect('cart')

        customer_email = form_data['email']
        if not customer_email and request.user.is_authenticated and request.user.email:
            customer_email = request.user.email

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            customer_name=form_data['name'],
            customer_email=customer_email,
            phone=form_data['phone'],
            country=form_data['country'],
            notes=form_data['notes'],
            payment_method=checkout_prefs['payment_method'],
            currency=checkout_prefs['currency'],
            total_amount=grand_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        )

        _create_order_items_and_reduce_stock(order, cart_items, checkout_prefs, product_map)

        # Clear the cart after a successful order capture.
        cart.items.all().delete()

    # Pesapal: hand off to the Node payments service and redirect the user.
    if checkout_prefs['payment_method'] == 'pesapal':
        import urllib.request as _url_req, json as _pay_json
        try:
            payload = _pay_json.dumps({
                'order_ref': order.order_ref,
                'amount': str(order.total_amount),
                'currency': order.currency,
                'customer': {
                    'name': order.customer_name,
                    'phone': order.phone,
                },
            }).encode()
            _req = _url_req.Request(
                settings.PESAPAL_INITIATE_URL,
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with _url_req.urlopen(_req, timeout=10) as _resp:
                _result = _pay_json.loads(_resp.read())
            if _result.get('redirect_url'):
                return redirect(_result['redirect_url'])
        except Exception as _e:
            logger.warning('Pesapal redirect failed: %s', _e)
            messages.warning(
                request,
                f'Pesapal is temporarily unavailable ({_e}). '
                'Your order is saved — please contact us to complete payment.',
            )

    return _render_checkout_success(
        request,
        order,
        checkout_prefs,
        grand_total,
        _payment_instructions(form_data['country'], checkout_prefs['payment_method']),
    )


def checkout(request):
    cart = _current_cart(request, create=False)
    if not cart or not cart.items.exists():
        messages.info(request, 'Your cart is empty. Add items before checkout.')
        return redirect('cart')

    checkout_prefs = _checkout_preferences(request)
    cart_items = list(cart.items.select_related('product'))

    stock_error = _validate_cart_stock(cart_items)
    if stock_error:
        messages.error(request, stock_error)
        return redirect('cart')

    items_view, grand_total = _build_checkout_items_view(cart_items, checkout_prefs)

    context = {
        'items_view': items_view,
        'currency': checkout_prefs['currency'],
        'payment_method': checkout_prefs['payment_method'],
        'grand_total_display': _format_money(grand_total, checkout_prefs['currency']),
        'form_data': {
            'name': '',
            'email': '',
            'phone': '',
            'country': '',
            'notes': '',
        },
    }

    if request.method == 'POST':
        return _checkout_post(request, cart, cart_items, checkout_prefs, grand_total, context)

    return render(request, 'core/checkout.html', context)


@require_POST
def update_cart_item(request, item_id):
    cart = _current_cart(request, create=False)
    if not cart:
        return redirect('cart')

    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity > 0:
        if quantity > item.product.stock_quantity:
            messages.error(request, f'Only {item.product.stock_quantity} unit(s) available for {item.product.name}.')
            return redirect('cart')
        item.quantity = quantity
        item.save()
    else:
        item.delete()
    return redirect('cart')


@require_POST
def remove_cart_item(request, item_id):
    cart = _current_cart(request, create=False)
    if not cart:
        return redirect('cart')

    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    return redirect('cart')


# ── Pesapal payment views ──────────────────────────────────────────────────────

from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@require_POST
def pesapal_ipn_callback(request):
    """Internal webhook: the Node payments service calls this after a Pesapal IPN."""
    import os
    expected_key = os.environ.get('INTERNAL_WEBHOOK_KEY', 'dev-internal-key')
    key = request.headers.get('X-Internal-Key', '')
    if key != expected_key:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        data = json.loads(request.body)
        order_ref  = data.get('order_ref')
        new_status = data.get('status')
        valid_statuses = (
            Order.STATUS_PENDING,
            Order.STATUS_CONFIRMED,
            Order.STATUS_FAILED,
        )
        if order_ref and new_status in valid_statuses:
            order = Order.objects.filter(order_ref=order_ref).first()
            if order:
                order.status = new_status
                order.save(update_fields=['status'])
        return JsonResponse({'ok': True})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


def pesapal_callback(request):
    """Pesapal redirects the customer here after the payment flow."""
    order_ref = request.GET.get('order_ref', '')
    order = Order.objects.filter(order_ref=order_ref).first()
    if not order:
        messages.error(request, 'Order not found.')
        return redirect('cart')
    return _render_checkout_success(
        request,
        order,
        None,
        None,
        'Your Pesapal payment is being verified. Your order status will update shortly.',
    )


# ---------------------------------------------------------------------------
# AI endpoints
# ---------------------------------------------------------------------------

from django.views.decorators.csrf import csrf_exempt  # noqa: E402 (already imported above via require_POST)


def _extract_measurements_cm(text):
    """Extract bust/waist/hips values in cm from free text."""
    raw = (text or '').lower()
    if not raw:
        return None

    patterns = {
        'bust': [r'\bbust\b\s*[:=,-]?\s*(\d{2,3}(?:\.\d+)?)', r'\bchest\b\s*[:=,-]?\s*(\d{2,3}(?:\.\d+)?)'],
        'waist': [r'\bwaist\b\s*[:=,-]?\s*(\d{2,3}(?:\.\d+)?)'],
        'hips': [r'\bhips?\b\s*[:=,-]?\s*(\d{2,3}(?:\.\d+)?)', r'\bhip\b\s*[:=,-]?\s*(\d{2,3}(?:\.\d+)?)'],
    }

    found = {}
    for key, key_patterns in patterns.items():
        for pat in key_patterns:
            m = re.search(pat, raw)
            if m:
                try:
                    found[key] = float(m.group(1))
                    break
                except (TypeError, ValueError):
                    continue

    if all(k in found for k in ('bust', 'waist', 'hips')):
        return found

    # Fallback: allow compact numeric format like "90 70 98" or "90/70/98".
    nums = re.findall(r'(\d{2,3}(?:\.\d+)?)', raw)
    if len(nums) >= 3:
        try:
            return {
                'bust': float(nums[0]),
                'waist': float(nums[1]),
                'hips': float(nums[2]),
            }
        except (TypeError, ValueError):
            return None

    return None


def _quick_chat_fallback(user_message):
    """Deterministic responses for common support queries when AI is unavailable."""
    msg = (user_message or '').strip().lower()
    if not msg:
        return ''

    # Numeric size query (e.g. "size 35")
    size_match = re.search(r'\b(?:size|saizi)\s*(\d{2})\b', msg)
    if size_match:
        try:
            requested = int(size_match.group(1))
            if requested < 32 or requested > 54:
                return 'Our EU sizes run from 32 to 54. Share bust, waist, and hips in cm for an exact fit recommendation.'
            if requested % 2 == 1:
                lower_even = requested - 1
                upper_even = requested + 1
                return (
                    f'EU {requested} is between sizes. We stock even EU sizes (32–54), so try EU {lower_even} '
                    f'for a snug fit or EU {upper_even} for a relaxed fit.'
                )
            return f'EU {requested} is available in our standard range. For best accuracy, share bust, waist, and hips in cm.'
        except (TypeError, ValueError):
            pass

    if any(token in msg for token in ('payment', 'pay', 'mtn', 'airtel', 'worldremit', 'pesapal')):
        return 'We accept MTN Mobile Money, Airtel Money, WorldRemit, and Pesapal.'

    if any(token in msg for token in ('delivery', 'deliver', 'shipping', 'ship', 'dispatch', 'pickup')):
        return (
            'Delivery is arranged after checkout confirmation. '
            'For local Kampala/nearby orders, we can use Boda (local motorcycle delivery). '
            'Add your country and notes at checkout, then we confirm dispatch details with you directly.'
        )

    if any(token in msg for token in ('currency', 'usd', 'eur', 'ugx', 'kes', 'mixed')):
        return (
            'You can browse prices in USD, EUR, KES, or UGX, but one order should use a single currency at checkout '
            'for accurate totals and payment confirmation.'
        )

    if any(token in msg for token in ('size', 'saizi', 'measure', 'measurement', 'bust', 'waist', 'hips', 'cm')):
        return 'Please share your bust, waist, and hips in cm, for example: bust 90, waist 70, hips 98.'

    return ''


@csrf_exempt
@require_POST
def api_chat(request):
    """
    POST /api/chat/
    Body: {"message": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}
    Returns: {"reply": "..."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = (body.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'message is required'}, status=400)

    # Deterministic size-assistance path: when measurements are present, return
    # an immediate size recommendation from the EU mapping table.
    measurement_intent = any(
        token in user_message.lower()
        for token in ('size', 'saizi', 'bust', 'waist', 'hips', 'measure', 'measurement', 'cm')
    )
    extracted = _extract_measurements_cm(user_message)
    if measurement_intent and extracted:
        bust = extracted['bust']
        waist = extracted['waist']
        hips = extracted['hips']
        if not (50 <= bust <= 200 and 40 <= waist <= 180 and 60 <= hips <= 220):
            return JsonResponse({
                'reply': 'Please send realistic measurements in centimeters, for example: bust 90, waist 70, hips 98.'
            })

        from core.ai_utils import recommend_size
        rec = recommend_size(bust, waist, hips)
        return JsonResponse({
            'reply': (
                f"Recommended EU size: {rec['size']}. {rec['note']} "
                'If you are between sizes, choose one size up for a relaxed fit.'
            )
        })

    history = body.get('history') or []
    if not isinstance(history, list):
        history = []

    # Build product catalog context (limit to 60 products to stay within token budget)
    catalog_lines = []
    for p in Product.objects.select_related('category').filter(in_stock=True).order_by('name')[:60]:
        sizes = p.sizes or 'various sizes'
        catalog_lines.append(
            f'- {p.name} | {p.category.name} | USD {p.price_usd} / UGX {p.price_ugx} '
            f'| Sizes: {sizes} | Stock: {p.stock_quantity} | Color: {p.color or "N/A"}'
        )

    catalog_text = '\n'.join(catalog_lines) if catalog_lines else 'No products currently in stock.'

    system_prompt = (
        "You are Kistie, a friendly AI shopping assistant for Kistie Store — a women's fashion boutique "
        "in Kampala, Uganda. You help customers find the right outfit, sizes, and prices. "
        "You can respond in English or Luganda depending on what the customer uses. "
        "Keep answers short and helpful. Payment methods accepted: MTN Mobile Money, Airtel Money, "
        "WorldRemit, and Pesapal. All sizes are EU standard (32–54).\n\n"
        "LIVE PRODUCT CATALOG:\n" + catalog_text
    )

    messages_payload = [{'role': 'system', 'content': system_prompt}]
    # Append last 6 turns of history to stay within token limits
    for turn in history[-6:]:
        role = turn.get('role', 'user')
        content = (turn.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            messages_payload.append({'role': role, 'content': content})
    messages_payload.append({'role': 'user', 'content': user_message})

    quick_reply = _quick_chat_fallback(user_message)
    if quick_reply:
        return JsonResponse({'reply': quick_reply})

    from core.ai_utils import chat_complete
    reply = chat_complete(messages_payload, max_tokens=300)

    if reply is None:
        return JsonResponse(
            {'reply': 'Sorry, the AI assistant is temporarily unavailable. Please contact us on WhatsApp.'},
        )
    return JsonResponse({'reply': reply})


@require_POST
@permission_required('core.access_staff_dashboard', raise_exception=True)
def api_ai_describe(request):
    """
    POST /api/ai/describe/
    Staff-only. Body: {"name": "...", "category": "...", "color": "...", "product_id": 5}
    Returns: {"description_en": "...", "description_lg": "..."}
    Optionally PATCHes the product's description field when product_id is supplied.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = (body.get('name') or '').strip()
    category = (body.get('category') or '').strip()
    color = (body.get('color') or '').strip()
    product_id = body.get('product_id')

    if not name:
        return JsonResponse({'error': 'name is required'}, status=400)

    from core.ai_utils import generate_product_description
    result = generate_product_description(name, category, color)

    if not result.get('description_en'):
        result = _fallback_ai_description(name, category, color)

    if product_id and result.get('description_en'):
        try:
            pid = int(product_id)
            Product.objects.filter(pk=pid).update(description=result['description_en'])
        except (TypeError, ValueError, Product.DoesNotExist):
            pass

    return JsonResponse(result)


@csrf_exempt
@require_POST
def api_size_recommend(request):
    """
    POST /api/size-recommend/
    Body: {"bust": 90, "waist": 70, "hips": 95}  (all in cm)
    Returns: {"size": "38", "note": "..."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        bust = float(body.get('bust', 0))
        waist = float(body.get('waist', 0))
        hips = float(body.get('hips', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'bust, waist, hips must be numbers (cm)'}, status=400)

    if not (50 <= bust <= 200 and 40 <= waist <= 180 and 60 <= hips <= 220):
        return JsonResponse({'error': 'Measurements out of plausible range (cm)'}, status=400)

    from core.ai_utils import recommend_size
    return JsonResponse(recommend_size(bust, waist, hips))
