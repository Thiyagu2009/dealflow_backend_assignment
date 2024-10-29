import json
import logging
import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from payments.models import Payment
from payments.models import PaymentLink
from payments.utils import get_payment_method_details

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    logger.info(f"Received request to handle stripe webhook: {request.body}")
    payload = request.body
    sig_header = request.headers.get('stripe-signature')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )

        # Handle the event based on its type
        print("event type", event.type)
        if event.type == 'payment_intent.succeeded':
            print("payment intent succeeded")
            handle_payment_success(event.data.object)
        elif event.type == 'payment_intent.payment_failed':
            handle_payment_failure(event.data.object)
        elif event.type == 'payment_intent.requires_action':
            handle_payment_action_required(event.data.object)
        
        logger.info("Webhook processed successfully")
        return HttpResponse(status=200)
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)
    

def handle_payment_success(payment_intent):
    """Handle successful payment"""
    try:
        # Get payment details
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        print("payment_intent", payment_intent)
        if not payment_link_id:
            logger.error("Payment link ID not found in metadata")
        try:   
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id)
        except PaymentLink.DoesNotExist:
            logger.error("Payment link not found")
            return HttpResponse(status=400)
        
        # Create payment record
        payment_method_info = get_payment_method_details(payment_intent)
        payment, created = Payment.objects.get_or_create(
            payment_link=payment_link,
            stripe_payment_id=payment_intent.id,
            defaults={
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency.upper(),
                'status': 'success',
                'payment_method': payment_method_info['type'],
                'metadata': {
                    'stripe_payment_method': payment_intent.payment_method,
                    'stripe_customer': payment_intent.customer,
                    'payment_method_details': json.dumps(payment_method_info['details'])
                }
            }
        )
        if not created:
            logger.info("Payment already exists, updating")
            payment.status = 'success'
            payment.metadata['stripe_payment_method'] = payment_intent.payment_method
            payment.metadata['stripe_customer'] = payment_intent.customer
            payment.metadata['payment_method_details'] = json.dumps(payment_method_info['details'])
            payment.amount = payment_intent.amount / 100
            payment.currency = payment_intent.currency.upper()
            payment.payment_method = payment_method_info['type']
            payment.save()
        
        # Update payment link status
        
        # Optional: Send success notification
        #send_payment_success_notification(payment_link)
        
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")
        print("payment success error", e)
        raise



def handle_payment_failure(payment_intent):
    """Handle failed payment"""
    try:
        logger.info(f"Received request to handle failed payment: {payment_intent}")
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        payment_link = PaymentLink.objects.get(unique_id=payment_link_id)
        payment_method_info = get_payment_method_details(payment_intent)

        if not payment_link_id:
            logger.error("Payment link ID not found in metadata")
            return HttpResponse(status=400)
        payment, created = Payment.objects.get_or_create(
            payment_link=payment_link,
            stripe_payment_id=payment_intent.id,
            defaults={
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency.upper(),
                'status': 'failed',
                'payment_method': payment_method_info['type'],
                'metadata': {
                    'error': payment_intent.last_payment_error,
                    'failure_code': payment_intent.last_payment_error.code if payment_intent.last_payment_error else None,
                }
            }
        )

        if not created:
            payment.status = 'failed'
            payment.amount = payment_intent.amount / 100
            payment.currency = payment_intent.currency.upper()
            payment.metadata['error'] = payment_intent.last_payment_error
            payment.metadata['failure_code'] = payment_intent.last_payment_error.code if payment_intent.last_payment_error else None
            payment.payment_method = payment_method_info['type']
            payment.save()
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")
        raise


def handle_payment_action_required(payment_intent):
    """Handle payments requiring additional action"""
    try:
        logger.info(f"Received request to handle payment action required: {payment_intent}")
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        if payment_link_id:
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id)
            Payment.objects.create(
                payment_link=payment_link,
                stripe_payment_id=payment_intent.id,
                amount=payment_intent.amount / 100,
                currency=payment_intent.currency.upper(),
                status='pending',
                
        )
            
        return HttpResponse(status=200)      
    except Exception as e:
        logger.error(f"Error handling payment action required: {str(e)}")
        raise
