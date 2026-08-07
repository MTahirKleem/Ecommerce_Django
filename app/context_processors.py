from django.conf import settings


def site_settings(request):
    return {
        'PAYPAL_CLIENT_ID': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
    }


def cart_total_amount(request):
    """Cart total for all users; ObjectId-safe session cart."""
    cart = request.session.get(getattr(settings, 'CART_SESSION_ID', 'cart'), {}) or {}
    total = 0.0
    for value in cart.values():
        if not value:
            continue
        try:
            total += float(value.get('price', 0)) * int(value.get('quantity', 0))
        except (TypeError, ValueError):
            continue
    return {'cart_total_amount': total}
