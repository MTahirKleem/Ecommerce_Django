# Register your models here.
from django.contrib import admin
from .models import *

class Product_Images(admin.TabularInline):
    model = Product_Image

class Additional_Informations(admin.TabularInline):
    model = Additional_Information

class Product_Admin(admin.ModelAdmin):
    inlines = (Product_Images,Additional_Informations)
    list_display = ('product_name', 'price', 'Categories', 'slug', 'Discount')
    list_editable = ('Categories',)

# Register your models here.
admin.site.register(slider)
admin.site.register(banner_area)
admin.site.register(Category)
# admin.site.register(Section)
admin.site.register(Product, Product_Admin)
admin.site.register(Product_Image)
admin.site.register(Additional_Information)