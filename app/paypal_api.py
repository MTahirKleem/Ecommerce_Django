import base64
import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


class PayPalAPIError(Exception):
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _safe_error_payload(payload):
    """Return a log-safe copy of a PayPal error payload (no secrets)."""
    if not isinstance(payload, dict):
        return {'raw': str(payload)[:500]}
    safe = {}
    for key in ('name', 'message', 'debug_id', 'details', 'error', 'error_description'):
        if key in payload:
            safe[key] = payload[key]
    return safe


def _request(method, path, access_token=None, data=None):
    url = f"{settings.PAYPAL_API_BASE}{path}"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'

    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode('utf-8')
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='ignore')
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {'raw': raw[:500]}
        logger.error(
            'PayPal HTTP error method=%s path=%s status=%s payload=%s',
            method,
            path,
            exc.code,
            _safe_error_payload(payload),
        )
        raise PayPalAPIError(
            payload.get('message') or payload.get('error_description') or str(exc),
            status_code=exc.code,
            payload=payload,
        ) from exc
    except URLError as exc:
        logger.error('PayPal connection failed method=%s path=%s reason=%s', method, path, exc.reason)
        raise PayPalAPIError(f'PayPal connection failed: {exc.reason}') from exc


def get_access_token():
    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    if not client_id or not client_secret:
        logger.error('PayPal OAuth failed: CLIENT_ID or CLIENT_SECRET missing')
        raise PayPalAPIError('PayPal CLIENT_ID / CLIENT_SECRET missing in .env')

    credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('ascii')
    url = f"{settings.PAYPAL_API_BASE}/v1/oauth2/token"
    headers = {
        'Authorization': f'Basic {credentials}',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    request = Request(
        url,
        data=b'grant_type=client_credentials',
        headers=headers,
        method='POST',
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='ignore')
        try:
            err_payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            err_payload = {'raw': raw[:300]}
        logger.error(
            'PayPal OAuth failed status=%s payload=%s',
            exc.code,
            _safe_error_payload(err_payload),
        )
        raise PayPalAPIError(
            f'PayPal auth failed ({exc.code})',
            status_code=exc.code,
            payload=err_payload,
        ) from exc
    except URLError as exc:
        logger.error('PayPal OAuth connection failed reason=%s', exc.reason)
        raise PayPalAPIError(f'PayPal connection failed: {exc.reason}') from exc

    token = payload.get('access_token')
    if not token:
        logger.error('PayPal OAuth response missing access_token keys=%s', list(payload.keys()))
        raise PayPalAPIError('PayPal auth response missing access_token', payload=payload)
    return token


def format_amount(value):
    amount = Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise PayPalAPIError('Order amount must be greater than zero')
    return f'{amount:.2f}'


def amounts_equal(left, right):
    try:
        a = Decimal(str(left)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        b = Decimal(str(right)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return False
    return a == b


def extract_capture_payment(capture_response):
    """
    Return (capture_id, amount_value, currency_code, capture_status) from a
    PayPal Orders v2 capture response.
    """
    purchase_units = capture_response.get('purchase_units') or []
    if not purchase_units:
        return '', '', '', ''
    payments = (purchase_units[0].get('payments') or {})
    captures = payments.get('captures') or []
    if not captures:
        return '', '', '', ''
    first = captures[0] or {}
    amount = first.get('amount') or {}
    return (
        first.get('id') or '',
        amount.get('value') or '',
        amount.get('currency_code') or '',
        (first.get('status') or '').upper(),
    )


def create_order(amount, currency=None, description='ShopAi order'):
    currency = currency or settings.PAYPAL_CURRENCY
    access_token = get_access_token()
    formatted = format_amount(amount)
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [
            {
                'description': description[:120],
                'amount': {
                    'currency_code': currency,
                    'value': formatted,
                },
            }
        ],
        'application_context': {
            'brand_name': 'ShopAi',
            'shipping_preference': 'NO_SHIPPING',
            'user_action': 'PAY_NOW',
        },
    }
    try:
        result = _request('POST', '/v2/checkout/orders', access_token=access_token, data=payload)
    except PayPalAPIError:
        logger.error(
            'PayPal create-order failed amount=%s currency=%s',
            formatted,
            currency,
        )
        raise
    if not result.get('id'):
        logger.error('PayPal create-order invalid response keys=%s', list(result.keys()))
    else:
        logger.info(
            'PayPal create-order ok id=%s status=%s amount=%s %s',
            result.get('id'),
            result.get('status'),
            formatted,
            currency,
        )
    return result


def capture_order(order_id):
    access_token = get_access_token()
    try:
        result = _request(
            'POST',
            f'/v2/checkout/orders/{order_id}/capture',
            access_token=access_token,
            data={},
        )
    except PayPalAPIError:
        logger.error('PayPal capture-order failed paypal_order_id=%s', order_id)
        raise
    logger.info(
        'PayPal capture-order response paypal_order_id=%s status=%s',
        order_id,
        result.get('status'),
    )
    return result


def cart_totals(cart):
    cart = cart or {}
    subtotal = 0.0
    shipping = 0.0
    names = []
    for item in cart.values():
        if not item:
            continue
        qty = int(item.get('quantity') or 0)
        price = float(item.get('price') or 0)
        subtotal += price * qty
        shipping += float(item.get('shipping_fee') or 0)
        name = item.get('name')
        if name:
            names.append(f'{name} x{qty}')
    return {
        'subtotal': subtotal,
        'shipping': shipping,
        'total': subtotal + shipping,
        'description': ', '.join(names)[:120] or 'ShopAi cart checkout',
        'names': names,
    }
