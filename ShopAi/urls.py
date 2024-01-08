from django.contrib import admin
from app import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from app.views import payment_completed_view, payment_failed_view, search_history
from app.views import order_history_view



urlpatterns = [

    # Error Page
    path('404', views.ERROR404, name='404'),

    # Admin URL
    path('admin/', admin.site.urls),
    #Base URL
    path('base/', views.BASE, name='base'),

    # Home and Other Page URLs
    path('', views.HOME, name='home'),
    path('about', views.ABOUT, name='about'),
    path('contect', views.CONTECT, name='contect'),
    path('product', views.PRODUCT, name='product'),

    path('product-details/<slug:slug>/', views.PRODUCT_DETAILS, name='product_detail'),


    # Account URLs
    path('account/my-account', views.MY_ACCOUNT, name='my_account'),
    path('account/register', views.REGISTER, name='handleregister'),
    path('account/login', views.LOGIN, name='handlelogin'),
    path('account/profile', views.PROFILE, name='profile'),
    path('account.profile/update', views.PROFILE_UPDATE, name='profile_update'),

    # Django Auth URLs
    path('accounts/', include('django.contrib.auth.urls')),

    # Cart URLs
    path('cart/add/<int:id>/', views.cart_add, name='cart_add'),
    path('cart/item_clear/<int:id>/', views.item_clear, name='item_clear'),
    path('cart/item_increment/<int:id>/', views.item_increment, name='item_increment'),
    path('cart/item_decrement/<int:id>/', views.item_decrement, name='item_decrement'),
    path('cart/cart_clear/', views.cart_clear, name='cart_clear'),
    path('cart/cart-detail/', views.cart_detail, name='cart_detail'),
    path('checkout', views.Checkout, name='checkout'),

    # PayPal URL
    path('paypal/', include('paypal.standard.ipn.urls')),

    # Payment URLs
    path('payment-completed/', payment_completed_view, name='payment_completed'),
    path('payment-failed/', payment_failed_view, name='payment_failed'),
    path('order-history/', order_history_view, name='order_history'),

    # Filter Product URLs
    path('product/filter-data', views.filter_data, name="filter-data"),

    # History URLs
    path('search/', views.SEARCH, name='search'),
    path('search-history/', search_history, name='search_history'),
    path('clear_search_history/', views.CLEAR, name='clear_search_history'),




] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
