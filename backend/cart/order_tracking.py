"""Order status timeline for customer-facing tracking UI."""

from .models import Order


TIMELINE_STEPS = (
    ('placed', 'Placed', 'Enteebedwa'),
    ('payment', 'Payment received', 'Okusasulwa kufunye'),
    ('packed', 'Packed', 'Tegekeddwa'),
    ('shipped', 'Shipped', 'Emereedde'),
    ('delivered', 'Delivered', 'Etuuse'),
)

_STATUS_RANK = {
    Order.STATUS_PENDING: 0,
    Order.STATUS_FAILED: 0,
    Order.STATUS_CONFIRMED: 1,
    Order.STATUS_PACKED: 2,
    Order.STATUS_SHIPPED: 3,
    Order.STATUS_DELIVERED: 4,
}


def _step_timestamp(order, step_key):
    mapping = {
        'placed': order.created_at,
        'payment': order.payment_confirmed_at,
        'packed': order.packed_at,
        'shipped': order.shipped_at,
        'delivered': order.delivered_at,
    }
    return mapping.get(step_key)


def order_timeline(order):
    """
    Return timeline steps for templates: label, state (complete|current|upcoming|failed), at, tracking_url.
    """
    if order.status == Order.STATUS_FAILED:
        return [
            {
                'key': 'placed',
                'label': 'Placed',
                'label_lg': 'Enteebedwa',
                'state': 'complete',
                'at': order.created_at,
            },
            {
                'key': 'payment',
                'label': 'Payment issue',
                'label_lg': 'Obuzibu ku kusasula',
                'state': 'failed',
                'at': None,
            },
        ]

    rank = _STATUS_RANK.get(order.status, 0)
    steps = []
    for index, (key, label, label_lg) in enumerate(TIMELINE_STEPS):
        step_rank = index
        if rank > step_rank:
            state = 'complete'
        elif rank == step_rank:
            state = 'current'
        else:
            state = 'upcoming'

        steps.append({
            'key': key,
            'label': label,
            'label_lg': label_lg,
            'state': state,
            'at': _step_timestamp(order, key),
            'show_tracking': key == 'shipped' and bool(order.tracking_url) and rank >= _STATUS_RANK[Order.STATUS_SHIPPED],
            'tracking_url': order.tracking_url if key == 'shipped' else '',
        })
    return steps


def orders_with_timelines(orders):
    """Attach .timeline_steps to each order for templates."""
    for order in orders:
        order.timeline_steps = order_timeline(order)
    return orders
