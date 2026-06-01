"""Session-backed recently viewed products for PDP / shop."""

from django.db.models import Prefetch

from inventory.models import Product, ProductImage

SESSION_KEY = 'recently_viewed_ids'
MAX_ITEMS = 12


def record_product_view(request, product_id):
    if not product_id:
        return
    ids = [int(product_id)]
    for raw in request.session.get(SESSION_KEY, []):
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            continue
        if pid != int(product_id):
            ids.append(pid)
    request.session[SESSION_KEY] = ids[:MAX_ITEMS]
    request.session.modified = True


def recently_viewed_products(request, exclude_product_id=None, limit=4):
    raw_ids = request.session.get(SESSION_KEY, [])
    ids = []
    for raw in raw_ids:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            continue
        if exclude_product_id and pid == int(exclude_product_id):
            continue
        if pid not in ids:
            ids.append(pid)
        if len(ids) >= limit:
            break

    if not ids:
        return Product.objects.none()

    preserved = {pk: index for index, pk in enumerate(ids)}
    qs = (
        Product.objects.filter(pk__in=ids, stock_quantity__gt=0)
        .prefetch_related(Prefetch('images', queryset=ProductImage.objects.order_by('id')))
    )
    products = list(qs)
    products.sort(key=lambda p: preserved.get(p.pk, 999))
    return products
