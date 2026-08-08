from django.db import models
from ckeditor.fields import RichTextField
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.contrib.auth.models import User



# Define the Slider model

class slider(models.Model):
    objects = models.Manager()
    DISCOUNT_DEAL = (
        ('HOT DEALS', 'HOT DEALS'),
        ('New Arraivels', 'New Arraivels'),
    )

    # Slider fields
    Image = models.ImageField(upload_to='slider_imgs')
    Discount_Deal = models.CharField(choices=DISCOUNT_DEAL, max_length=100)
    SALE = models.IntegerField()
    Brand_Name = models.CharField(max_length=200)
    Discount = models.IntegerField()
    Link = models.CharField(max_length=200)

    def __str__(self):
        return self.Brand_Name


# Define the BannerArea model
class banner_area(models.Model):
    objects = models.Manager()

    # BannerArea fields
    image = models.ImageField(upload_to='banner_img')
    Discount_Deal = models.CharField(max_length=100)
    Quote = models.CharField(max_length=100)
    Discount = models.IntegerField()

    def __str__(self):
        return self.Quote


# Define the Category model
class Category(models.Model):
    objects = models.Manager()

    # Category fields
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Define the Section model
class Section(models.Model):
    # Section fields
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Define the Product model
class Product(models.Model):
    objects = models.Manager()

    # Product fields
    total_quantity = models.IntegerField()
    Availability = models.IntegerField()
    featured_image = models.ImageField(upload_to='featured_image', blank=True, null=True,
                                       default='featured_image/default.jpg')
    product_name = models.CharField(max_length=100)
    price = models.IntegerField()
    Discount = models.IntegerField()
    shipping_fee = models.IntegerField(null=True)
    model_Name = models.CharField(max_length=100)
    Categories = models.ForeignKey(Category, on_delete=models.CASCADE)
    Description = RichTextField()
    slug = models.SlugField(default='', max_length=500, null=True, blank=True)

    def __str__(self):
        return self.product_name

    # Aliases expected by django-shopping-cart
    @property
    def name(self):
        return self.product_name

    @property
    def image(self):
        return self.featured_image

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("product_detail", kwargs={'slug': self.slug})

    class Meta:
        db_table = "app_Product"

# Define the create_slug function
def create_slug(instance, new_slug=None):
    slug = slugify(instance.product_name)
    if new_slug is not None:
        slug = new_slug
    qs = Product.objects.filter(slug=slug).order_by('-id')
    exists = qs.exists()
    if exists:
        new_slug = "%s-%s" % (slug, qs.first().id)
        return create_slug(instance, new_slug=new_slug)
    return slug


# Define the pre_save_post_receiver function
def pre_save_post_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = create_slug(instance)


# Connect the pre_save_post_receiver function to the pre_save signal of the Product model
pre_save.connect(pre_save_post_receiver, Product)


# Define the Product_Image model
class Product_Image(models.Model):
    # Product_Image fields
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    Image_url = models.ImageField(upload_to='image_url')


# Define the Additional_Information model
class Additional_Information(models.Model):
    # Additional_Information fields
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    specification = models.CharField(max_length=100)
    detail = models.CharField(max_length=100)


# Define the Order model
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    objects = models.Manager()

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product_name = models.CharField(max_length=500)
    order_date = models.DateTimeField(auto_now_add=True)
    paypal_order_id = models.CharField(max_length=100, blank=True, default='')
    paypal_capture_id = models.CharField(max_length=100, blank=True, default='')
    total_amount = models.CharField(max_length=50, blank=True, default='0')
    currency = models.CharField(max_length=10, blank=True, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payer_email = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.product_name


# Define the SearchHistory model
class SearchHistory(models.Model):
    objects = models.Manager()

    # SearchHistory fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.query}'


# Define the UserInteraction model
class UserInteraction(models.Model):
    objects = models.Manager()

    # UserInteraction fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=100)
    interaction_timestamp = models.DateTimeField(auto_now_add=True)