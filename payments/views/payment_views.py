import logging
import stripe

from datetime import datetime
from django.conf import settings
from django.http import  JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from dealflow.throttlers import PaymentAnonThrottle, PaymentUserThrottle
from payments.models import PaymentLink
from payments.serializers.payment_serializers import PaymentLinkCreateSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentUserThrottle])
def create_payment_link(request):
    """
    Create a payment link
    """
    try:
        logger.info(f"Received request to create payment link: {request.data}")
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        description = request.data.get('description', '')
        expiration_date = request.data.get('expiration_date')

        serializer = PaymentLinkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors
            }, status=400)
        
        payment_link = PaymentLink.objects.create(
            user=request.user,
            amount=amount,
            currency=currency,
            description=description,
            expiration_date=expiration_date
        )
        
        return JsonResponse({
            'status': 'success',
            'payment_url': request.build_absolute_uri(payment_link.get_absolute_url()),
            'payment_id': payment_link.unique_id
        })
        
    except Exception as e:
        logger.error(f"Error creating payment link: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@permission_classes([AllowAny])
@require_http_methods(["GET"])
@throttle_classes([PaymentAnonThrottle])
def payment_page(request, payment_id):
    """
    Render the payment page
    """
    try:
        logger.info(f"Received request to render payment page: {payment_id}")
        payment_link = get_object_or_404(PaymentLink, unique_id=payment_id)

        if  payment_link.expiration_date < datetime.now().date():
            logger.info(f"Payment link expired: {payment_id}")
            return render(request, 'payments/error.html', {'error': 'Payment link expired'})
        elif payment_link.status == 'active':
            logger.info(f"Payment link active: {payment_id}")
            return render(request, 'payments/payment_page.html', {
                'payment': payment_link,
                'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY
            })
    except PaymentLink.DoesNotExist:
        logger.info(f"Payment link not found: {payment_id}")
        return render(request, 'payments/broken_link.html')
    except Exception as e:
        logger.error(f"Error rendering payment page: {str(e)}")
        return render(request, 'payments/broken_link.html')


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PaymentAnonThrottle])
def create_payment_intent(request, payment_id):
    """
    Create a payment intent
    """
    try:
        logger.info(f"Received request to create payment intent: {payment_id}")
        # Find payment link
        payment_link = get_object_or_404(PaymentLink, unique_id=payment_id)
        
        # Create payment intent
        intent =stripe.PaymentIntent.create(
            amount=int(float(payment_link.amount) * 100),  # Convert to cents
            currency=payment_link.currency.lower(),
            payment_method_types=[
                'card',
                'amazon_pay',
            ],
            metadata={
                'payment_link_id': payment_link.unique_id
            },
        )
        
        return JsonResponse({
            'clientSecret': intent.client_secret
        })
        
    except PaymentLink.DoesNotExist:
        logger.info(f"Payment link not found: {payment_id}")
        return JsonResponse({
            'error': 'Payment link not found'
        }, status=404)
        
    except stripe.error.StripeError as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred'
        }, status=500)
    

@permission_classes([AllowAny])
@throttle_classes([PaymentAnonThrottle])
def payment_completed(request):
    """
    Handle the payment success
    """
    logger.info(f"Received request to handle payment completed: {request.GET}")
    payment_intent_id = request.GET.get('payment_intent')
    status = request.GET.get('redirect_status')
    
    try:
        # Retrieve the payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        logger.info(f"Payment intent status: {payment_intent.status}")
        # Get the payment link ID from metadata
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        
        if payment_link_id:
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id, status="active")
            # Create or update payment record
            if status == 'succeeded':  
                logger.info(f"Payment succeeded: {payment_link_id}")
                return render(request, 'payments/success.html', {
                    'amount': payment_intent.amount / 100,
                    'currency': payment_intent.currency.upper(),
                })
            elif status == 'failed':
                logger.info(f"Payment failed: {payment_link_id}")
                return render(request, 'payments/error.html', {'error': 'Payment failed'})
            elif status == 'requires_action':
                logger.info(f"Payment requires action: {payment_link_id}")
                return render(request, 'payments/error.html', {'error': 'Payment requires action'})
            else:
                logger.info(f"Payment status unknown: {payment_link_id}")
                return render(request, 'payments/error.html', {'error': 'Payment status unknown'})
    except stripe.error.StripeError as e:
        logger.error(f"Error handling payment completed: {str(e)}")
        return render(request, 'payments/error.html', {'error': str(e)})
    except PaymentLink.DoesNotExist:
        logger.info(f"Payment link not found: {payment_link_id}")
        return render(request, 'payments/error.html', {'error': 'Payment not found'})
    except Exception as e:
        logger.error(f"Error handling payment completed: {str(e)}")
        return render(request, 'payments/error.html', {'error': 'An error occurred'})
    

