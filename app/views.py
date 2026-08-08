import json
import logging

from app.models import slider, banner_area, Product, Category, SearchHistory
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from app.models import Order
from app.mongo_cart import MongoCart
from app.paypal_api import (
    PayPalAPIError,
    amounts_equal,
    capture_order,
    cart_totals,
    create_order,
    extract_capture_payment,
    format_amount,
)
from django.template.loader import render_to_string
from src.utlis.utils import get_recommendations
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import UserInteraction, Product
from django.http import JsonResponse, Http404

logger = logging.getLogger(__name__)


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
    cart = MongoCart(request)
    product = Product.objects.get(id=id)
    cart.add(product=product)
    return redirect("cart_detail")


def item_clear(request, id):
    cart = MongoCart(request)
    product = Product.objects.get(id=id)
    cart.remove(product)
    return redirect("cart_detail")


def item_increment(request, id):
    cart = MongoCart(request)
    product = Product.objects.get(id=id)
    cart.add(product=product)
    return redirect("cart_detail")


def item_decrement(request, id):
    cart = MongoCart(request)
    product = Product.objects.get(id=id)
    cart.decrement(product=product)
    return redirect("cart_detail")


def cart_clear(request):
    cart = MongoCart(request)
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
    cart = request.session.get(settings.CART_SESSION_ID, {}) or {}
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_detail')

    totals = cart_totals(cart)
    context = {
        'cart': cart,
        'shipping_fee': totals['shipping'],
        'cart_total_amount': totals['subtotal'],
        'order_total': totals['total'],
        'paypal_currency': settings.PAYPAL_CURRENCY,
        'paypal_mode': settings.PAYPAL_MODE,
    }
    return render(request, 'checkout/checkout.html', context)


def _paypal_user(request):
    return request.user if request.user.is_authenticated else None


def _mark_order_failed(request, *, paypal_order_id, product_name, amount, currency, capture_id='', payer_email='', reason=''):
    """Create or update a single Order row as failed (no duplicates for same paypal_order_id)."""
    existing = Order.objects.filter(paypal_order_id=paypal_order_id).first() if paypal_order_id else None
    if existing:
        if existing.status != 'paid':
            existing.status = 'failed'
            if capture_id:
                existing.paypal_capture_id = capture_id
            if payer_email:
                existing.payer_email = payer_email
            existing.total_amount = amount
            existing.currency = currency
            existing.save()
        logger.warning(
            'PayPal order marked failed paypal_order_id=%s reason=%s',
            paypal_order_id,
            reason,
        )
        return existing

    order = Order.objects.create(
        user=_paypal_user(request),
        product_name=product_name or 'ShopAi checkout',
        paypal_order_id=paypal_order_id or '',
        paypal_capture_id=capture_id or '',
        total_amount=amount,
        currency=currency,
        status='failed',
        payer_email=payer_email or '',
    )
    logger.warning(
        'PayPal failed order created id=%s paypal_order_id=%s reason=%s',
        order.id,
        paypal_order_id,
        reason,
    )
    return order


@require_POST
def paypal_create_order(request):
    cart = request.session.get(settings.CART_SESSION_ID, {}) or {}
    totals = cart_totals(cart)
    if totals['total'] <= 0:
        logger.warning('PayPal create-order rejected: empty cart')
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    expected_amount = format_amount(totals['total'])
    expected_currency = settings.PAYPAL_CURRENCY

    try:
        order = create_order(
            amount=expected_amount,
            currency=expected_currency,
            description=totals['description'],
        )
    except PayPalAPIError as exc:
        logger.error('PayPal create-order view failed: %s', exc)
        return JsonResponse({'error': str(exc)}, status=400)

    order_id = order.get('id')
    if not order_id:
        logger.error('PayPal create-order invalid response: missing id')
        return JsonResponse({'error': 'PayPal did not return an order id'}, status=400)

    request.session['pending_paypal_order_id'] = order_id
    request.session['pending_paypal_amount'] = expected_amount
    request.session['pending_paypal_currency'] = expected_currency
    request.session.modified = True
    return JsonResponse({'id': order_id})


@require_POST
def paypal_capture_order(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        payload = {}

    order_id = payload.get('orderID') or request.POST.get('orderID')
    if not order_id:
        logger.error('PayPal capture rejected: missing orderID')
        return JsonResponse({'error': 'Missing PayPal orderID'}, status=400)

    pending_id = request.session.get('pending_paypal_order_id')
    if pending_id and pending_id != order_id:
        logger.error(
            'PayPal capture rejected: order mismatch pending=%s got=%s',
            pending_id,
            order_id,
        )
        return JsonResponse({'error': 'PayPal order mismatch'}, status=400)

    cart = request.session.get(settings.CART_SESSION_ID, {}) or {}
    totals = cart_totals(cart)
    expected_amount = request.session.get('pending_paypal_amount') or format_amount(totals['total'])
    expected_currency = (
        request.session.get('pending_paypal_currency')
        or settings.PAYPAL_CURRENCY
    )
    product_summary = totals['description']

    try:
        capture = capture_order(order_id)
    except PayPalAPIError as exc:
        _mark_order_failed(
            request,
            paypal_order_id=order_id,
            product_name=product_summary,
            amount=expected_amount,
            currency=expected_currency,
            reason=str(exc),
        )
        logger.error('PayPal capture API failed paypal_order_id=%s error=%s', order_id, exc)
        return JsonResponse({'error': str(exc)}, status=400)

    status = (capture.get('status') or '').upper()
    capture_id, captured_amount, captured_currency, capture_status = extract_capture_payment(capture)
    payer = capture.get('payer') or {}
    payer_email = payer.get('email_address') or ''

    if status != 'COMPLETED':
        _mark_order_failed(
            request,
            paypal_order_id=order_id,
            product_name=product_summary,
            amount=expected_amount,
            currency=expected_currency,
            capture_id=capture_id,
            payer_email=payer_email,
            reason=f'status={status or "unknown"}',
        )
        logger.error(
            'PayPal capture not COMPLETED paypal_order_id=%s status=%s',
            order_id,
            status or 'unknown',
        )
        return JsonResponse(
            {'error': f'Payment not completed ({status or "unknown"})'},
            status=400,
        )

    if not amounts_equal(captured_amount, expected_amount):
        _mark_order_failed(
            request,
            paypal_order_id=order_id,
            product_name=product_summary,
            amount=expected_amount,
            currency=expected_currency,
            capture_id=capture_id,
            payer_email=payer_email,
            reason=f'amount mismatch captured={captured_amount} expected={expected_amount}',
        )
        logger.error(
            'PayPal amount mismatch paypal_order_id=%s captured=%s expected=%s',
            order_id,
            captured_amount,
            expected_amount,
        )
        return JsonResponse(
            {'error': 'Payment amount mismatch. Order was not marked as paid.'},
            status=400,
        )

    if (captured_currency or '').upper() != (expected_currency or '').upper():
        _mark_order_failed(
            request,
            paypal_order_id=order_id,
            product_name=product_summary,
            amount=expected_amount,
            currency=expected_currency,
            capture_id=capture_id,
            payer_email=payer_email,
            reason=f'currency mismatch captured={captured_currency} expected={expected_currency}',
        )
        logger.error(
            'PayPal currency mismatch paypal_order_id=%s captured=%s expected=%s',
            order_id,
            captured_currency,
            expected_currency,
        )
        return JsonResponse(
            {'error': 'Payment currency mismatch. Order was not marked as paid.'},
            status=400,
        )

    if capture_status and capture_status != 'COMPLETED':
        _mark_order_failed(
            request,
            paypal_order_id=order_id,
            product_name=product_summary,
            amount=expected_amount,
            currency=expected_currency,
            capture_id=capture_id,
            payer_email=payer_email,
            reason=f'capture_status={capture_status}',
        )
        logger.error(
            'PayPal capture unit not COMPLETED paypal_order_id=%s capture_status=%s',
            order_id,
            capture_status,
        )
        return JsonResponse(
            {'error': f'Payment capture not completed ({capture_status})'},
            status=400,
        )

    existing = Order.objects.filter(paypal_order_id=order_id).first()
    if existing and existing.status == 'paid':
        logger.info('PayPal capture idempotent hit paypal_order_id=%s', order_id)
        return JsonResponse({
            'status': 'COMPLETED',
            'order_id': str(existing.id),
            'paypal_order_id': order_id,
            'redirect_url': '/payment-completed/',
        })

    if existing:
        existing.user = _paypal_user(request) or existing.user
        existing.product_name = product_summary
        existing.paypal_capture_id = capture_id or ''
        existing.total_amount = expected_amount
        existing.currency = expected_currency
        existing.status = 'paid'
        existing.payer_email = payer_email
        existing.save()
        order = existing
    else:
        order = Order.objects.create(
            user=_paypal_user(request),
            product_name=product_summary,
            paypal_order_id=order_id,
            paypal_capture_id=capture_id or '',
            total_amount=expected_amount,
            currency=expected_currency,
            status='paid',
            payer_email=payer_email,
        )

    request.session[settings.CART_SESSION_ID] = {}
    request.session.pop('pending_paypal_order_id', None)
    request.session.pop('pending_paypal_amount', None)
    request.session.pop('pending_paypal_currency', None)
    request.session.modified = True

    logger.info(
        'PayPal payment paid order_id=%s paypal_order_id=%s amount=%s %s',
        order.id,
        order_id,
        expected_amount,
        expected_currency,
    )
    return JsonResponse({
        'status': 'COMPLETED',
        'order_id': str(order.id),
        'paypal_order_id': order_id,
        'redirect_url': '/payment-completed/',
    })


def payment_completed_view(request):
    return render(request, 'core/payment-completed.html')


def payment_failed_view(request):
    return render(request, 'core/payment-failed.html')


@login_required(login_url='/accounts/login/')
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