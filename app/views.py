from app.models import slider, banner_area, Product, Category, SearchHistory
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.cart import Cart
from django.shortcuts import render, redirect, get_object_or_404
from app.models import Order
from django.template.loader import render_to_string
from src.utlis.utils import get_recommendations
import pandas as pd
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import UserInteraction, Product
from django.http import JsonResponse, Http404


def BASE(request):
    return render(request, 'base.html')


def HOME(request):
    sliders = slider.objects.all().order_by('id')
    banners = banner_area.objects.all().order_by('id')
    product = Product.objects.all().order_by('-id')[:8]

    categories = Category.objects.all()

    context = {
        'sliders': sliders,
        'banners': banners,
        'product': product,

        'categories': categories,
    }
    return render(request, 'Main/home.html', context)


def PRODUCT_DETAILS(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        raise Http404("Product does not exist")
    except Product.MultipleObjectsReturned:
        # Handle multiple objects returned, perhaps choose the first one
        product = Product.objects.filter(slug=slug).first()

    context = {
        'product': product,
    }

    return render(request, 'product/product_detail.html', context)


def ERROR404(request):
    return render(request, 'error/404.html')


def MY_ACCOUNT(request):
    return render(request, 'account/my-account.html')


def REGISTER(request):
    if request.method == "POST":
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'username is already exist')
            return redirect('login')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'email is already exist')
            return redirect('login')

        user = User(
            username=username,
            email=email,
            first_name=firstname,
            last_name=lastname,
        )
        user.set_password(password)
        user.save()

        return redirect('login')


def LOGIN(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Email and Password Are Invalid ')
            return redirect('login')


@login_required(login_url='/accounts/login/')
def PROFILE(request):
    return render(request, 'profile/profile.html')


@login_required(login_url='/accounts/login/')
def PROFILE_UPDATE(request):
    if request.method == "POST":
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_id = request.user.id

        user = User.objects.get(id=user_id)
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email

        if password != None and password != "":
            user.set_password(password)
        user.save()
        messages.success(request, 'Profile are successfully Updated')
        return redirect('profile')


def cart_add(request, id):
    cart = Cart(request)
    product = Product.objects.get(id=id)
    cart.add(product=product)
    return redirect("cart_detail")


def item_clear(request, id):
    cart = Cart(request)
    product = Product.objects.get(id=id)
    cart.remove(product)
    return redirect("cart_detail")


def item_increment(request, id):
    cart = Cart(request)
    product = Product.objects.get(id=id)
    cart.add(product=product)
    return redirect("cart_detail")


def item_decrement(request, id):
    cart = Cart(request)
    product = Product.objects.get(id=id)
    cart.decrement(product=product)
    return redirect("cart_detail")


def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return redirect("cart_detail")


def cart_detail(request):
    cart = request.session.get('cart', {})
    shipping_fee = sum(i.get('shipping_fee', 0) or 0 for i in cart.values() if i)
    context = {
        'shipping_fee': shipping_fee,
    }
    return render(request, 'cart/cart.html', context)


def Checkout(request):
    cart = request.session.get('cart')
    shipping_fee = sum(i.get('shipping_fee', 0) or 0 for i in cart.values() if i)
    context = {
        'shipping_fee': shipping_fee,

    }
    return render(request, 'checkout/checkout.html', context)


def payment_completed_view(request):
    return render(request, 'core/payment-completed.html')


def payment_failed_view(request):
    return render(request, 'core/payment-failed.html')


def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, "order_history.html", {'orders': orders})


def ABOUT(request):
    return render(request, 'Main/about.html')


def CONTECT(request):
    return render(request, 'Main/contect.html')


def PRODUCT(request):
    category = Category.objects.all()

    product = Product.objects.all()
    paginator = Paginator(product, 52)
    page = request.GET.get('page')
    page_product = paginator.get_page(page)


    context = {
        'category': category,
        'product': page_product,
    }
    return render(request, 'product/product.html', context)


def filter_data(request):
    categories = request.GET.getlist('category[]')
    brands = request.GET.getlist('model_Name[]')

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    allProducts = Product.objects.all().order_by('-id').distinct()

    # Apply category filter
    if len(categories) > 0:
        allProducts = allProducts.filter(categories__id__in=categories).distinct()

    # Apply brand filter
    if len(brands) > 0:
        allProducts = allProducts.filter(brand__id__in=brands).distinct()

    # Apply price filter
    if min_price is not None:
        allProducts = allProducts.filter(price__gte=min_price)

    if max_price is not None:
        allProducts = allProducts.filter(price__lte=max_price)

    rendered_products = render_to_string('ajax/product.html', {'product': allProducts})

    return JsonResponse({'data': rendered_products})

# views.py



def SEARCH(request):
    query = request.GET.get('query', '')
    user_id = request.user.id
    recommended_product_ids = get_recommendations(user_id, query)

    recommended_products = Product.objects.filter(id__in=recommended_product_ids)

    return render(request, 'Main/search.html', {'products': recommended_products, 'query': query})




def search_history(request):
    if request.user.is_authenticated:
        search_history = SearchHistory.objects.filter(user=request.user).order_by('-timestamp')
        print(f"User: {request.user.username}, Search History: {search_history}")
    else:
        search_history = None

    context = {
        'search_history': search_history,
    }

    return render(request, 'Main/search_history.html', context)



def CLEAR(request):
    SearchHistory.objects.filter(user=request.user).delete()
    return redirect('search_history')


def record_user_interaction(request, product_id):
    user = request.user
    product = get_object_or_404(Product, pk=product_id)

    # Save user interaction
    UserInteraction.objects.create(user=user, product=product)

    return JsonResponse({'status': 'success'})



def home(request):
    recommended_products = []

    if request.user.is_authenticated:
        # Retrieve user's search history
        user_searches = SearchHistory.objects.filter(user=request.user)

        # Extract product categories from user's search history
        user_categories = [search.query for search in user_searches]

        # Print categories for debugging
        print(f"User Categories: {user_categories}")

        # Find products related to user's search history (content-based recommendation)
        recommended_products = Product.objects.filter(Categories__name__in=user_categories).distinct()

    # Print recommended products for debugging
    print(f"Recommended Products: {recommended_products}")

    return render(request, 'home.html', {'recommended_products': recommended_products})