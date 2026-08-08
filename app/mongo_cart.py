from django.conf import settings


def _json_safe(value):
    """Convert MongoDB ObjectIds / non-JSON values for Django sessions."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class MongoCart:
    """Session cart that stores MongoDB ObjectId keys as strings."""

    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, action=None):
        product_id = str(product.id)
        image_url = ''
        if product.featured_image:
            try:
                image_url = product.featured_image.url
            except ValueError:
                image_url = str(product.featured_image)

        user_id = None
        if self.request.user.is_authenticated:
            user_id = _json_safe(self.request.user.id)

        if product_id not in self.cart:
            self.cart[product_id] = {
                'userid': user_id,
                'product_id': product_id,
                'name': product.product_name,
                'quantity': int(quantity),
                'price': str(product.price),
                'shipping_fee': int(product.shipping_fee or 0),
                'image': image_url,
                'featured_image': image_url,
            }
        else:
            self.cart[product_id]['quantity'] = int(self.cart[product_id].get('quantity', 0)) + int(quantity)
            # Repair any previously stored ObjectId values
            self.cart[product_id]['userid'] = user_id
            self.cart[product_id]['product_id'] = product_id
        self.save()

    def save(self):
        safe_cart = {}
        for key, value in self.cart.items():
            if not isinstance(value, dict):
                continue
            safe_cart[str(key)] = {
                'userid': _json_safe(value.get('userid')),
                'product_id': _json_safe(value.get('product_id')),
                'name': str(value.get('name', '')),
                'quantity': int(value.get('quantity') or 0),
                'price': str(value.get('price', '0')),
                'shipping_fee': int(value.get('shipping_fee') or 0),
                'image': str(value.get('image') or ''),
                'featured_image': str(value.get('featured_image') or value.get('image') or ''),
            }
        self.cart = safe_cart
        self.session[settings.CART_SESSION_ID] = safe_cart
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def decrement(self, product):
        product_id = str(product.id)
        if product_id not in self.cart:
            return
        self.cart[product_id]['quantity'] -= 1
        if self.cart[product_id]['quantity'] < 1:
            del self.cart[product_id]
        self.save()

    def clear(self):
        self.session[settings.CART_SESSION_ID] = {}
        self.session.modified = True
