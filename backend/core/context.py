from django.conf import settings

from cart.whatsapp import format_store_phone_display, store_whatsapp_number, whatsapp_url


def _instagram_handle(profile_url):
    url = (profile_url or '').rstrip('/')
    if 'instagram.com/' in url:
        return url.split('instagram.com/')[-1].split('?')[0] or 'Instagram'
    return 'Instagram'


def feature_flags(_request):
    profile_url = getattr(settings, 'INSTAGRAM_PROFILE_URL', '')
    wa_digits = store_whatsapp_number()
    return {
        'ENABLE_ADMIN': settings.ENABLE_ADMIN,
        'instagram_url': profile_url,
        'instagram_handle': _instagram_handle(profile_url),
        'whatsapp_store_digits': wa_digits,
        'whatsapp_store_url': whatsapp_url(wa_digits, ''),
        'whatsapp_store_display': format_store_phone_display(wa_digits),
    }
