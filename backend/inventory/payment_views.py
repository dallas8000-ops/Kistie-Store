import json
import logging
from decimal import Decimal, InvalidOperation
from uuid import uuid4
import urllib.request

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


logger = logging.getLogger(__name__)


class PaymentCheckoutGateway(APIView):
    """Initiate online checkout and return a gateway redirect URL."""

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        payment_method = str(data.get('payment_method') or 'pesapal').strip().lower()
        if payment_method != 'pesapal':
            return Response(
                {
                    'automated': False,
                    'payment_method': payment_method,
                    'message': (
                        'Automated gateway is currently available for Pesapal only. '
                        'Use checkout instructions for MTN, Airtel, or WorldRemit.'
                    ),
                },
                status=status.HTTP_200_OK,
            )

        raw_amount = data.get('amount')
        if raw_amount is None:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'amount must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'error': 'amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        currency = str(data.get('currency') or 'USD').strip().upper()
        order_ref = str(data.get('order_ref') or f'KS-{uuid4().hex[:8].upper()}').strip()

        initiate_url = str(getattr(settings, 'PESAPAL_INITIATE_URL', '')).strip()
        if not initiate_url:
            return Response(
                {'error': 'PESAPAL_INITIATE_URL is not configured on the server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        customer = data.get('customer') or {}
        payload = {
            'order_ref': order_ref,
            'amount': str(amount.quantize(Decimal('0.01'))),
            'currency': currency,
            'customer': {
                'name': str(customer.get('name') or 'Store Customer').strip(),
                'email': str(customer.get('email') or '').strip(),
                'phone': str(customer.get('phone') or '').strip(),
            },
        }

        try:
            req = urllib.request.Request(
                initiate_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                gateway_response = json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            logger.warning('Pesapal initiation failed for %s: %s', order_ref, exc)
            return Response(
                {'error': 'Unable to start Pesapal checkout right now. Please retry shortly.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        redirect_url = gateway_response.get('redirect_url')
        if not redirect_url:
            logger.warning('Pesapal initiation returned no redirect_url for %s', order_ref)
            return Response(
                {'error': 'Gateway did not return a redirect URL.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'automated': True,
                'provider': 'pesapal',
                'order_ref': order_ref,
                'payment_method': payment_method,
                'redirect_url': redirect_url,
                'gateway': {
                    'order_tracking_id': gateway_response.get('order_tracking_id'),
                },
            },
            status=status.HTTP_200_OK,
        )
