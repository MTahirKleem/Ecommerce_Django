from django.conf import settings


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

        if product_id not in self.cart:
            self.cart[product_id] = {
                'userid': self.request.user.id if self.request.user.is_authenticated else None,
                'product_id': product_id,
                'name': product.product_name,
                'quantity': quantity,
                'price': str(product.price),
                'shipping_fee': product.shipping_fee or 0,
                'image': image_url,
                'featured_image': image_url,
            }
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
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
