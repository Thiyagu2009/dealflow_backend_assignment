from datetime import datetime, timezone
import json

from django.urls import reverse
import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from dealflow.throttlers import PaymentAnonThrottle, PaymentUserThrottle
from payments.models import Payment, PaymentLink
from payments.serializers.payment_serializers import PaymentLinkCreateSerializer
from payments.utils import convert_to_usd, get_payment_method_details

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentUserThrottle])
def create_payment_link(request):
    """
    Create a payment link
    """
    try:
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
        payment_link = get_object_or_404(PaymentLink, unique_id=payment_id)
        print("expiration date", payment_link.expiration_date)
        if  payment_link.expiration_date < datetime.now().date():
            payment_link.save()
            return render(request, 'payments/error.html', {'error': 'Payment link expired'})
        elif payment_link.status == 'active':
            return render(request, 'payments/payment_page.html', {
                'payment': payment_link,
                'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY
            })
    except PaymentLink.DoesNotExist:
        return render(request, 'payments/broken_link.html')
    except Exception as e:
        print(e)
        return render(request, 'payments/broken_link.html')


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PaymentAnonThrottle])
def create_payment_intent(request, payment_id):
    """
    Create a payment intent
    """
    try:
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
        return JsonResponse({
            'error': 'Payment link not found'
        }, status=404)
        
    except stripe.error.StripeError as e:
        print(e)
        return JsonResponse({
            'error': str(e)
        }, status=400)
        
    except Exception as e:
        print(e)
        return JsonResponse({
            'error': 'An error occurred'
        }, status=500)
    

@permission_classes([AllowAny])
@throttle_classes([PaymentAnonThrottle])
def payment_completed(request):
    """
    Handle the payment success
    """
    payment_intent_id = request.GET.get('payment_intent')
    status = request.GET.get('redirect_status')
    
    try:
        # Retrieve the payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        print("payment intent", payment_intent.status)
        # Get the payment link ID from metadata
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        
        if payment_link_id:
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id, status="active")
            # Create or update payment record
            if status == 'succeeded':  
                return render(request, 'payments/success.html', {
                    'amount': payment_intent.amount / 100,
                    'currency': payment_intent.currency.upper(),
                })
            elif status == 'failed':
                return render(request, 'payments/error.html', {'error': 'Payment failed'})
            elif status == 'requires_action':
                return render(request, 'payments/error.html', {'error': 'Payment requires action'})
            else:
                return render(request, 'payments/error.html', {'error': 'Payment status unknown'})
    except stripe.error.StripeError as e:
        print(e)
        return render(request, 'payments/error.html', {'error': str(e)})
    except PaymentLink.DoesNotExist:
        return render(request, 'payments/error.html', {'error': 'Payment not found'})
    except Exception as e:
        print(e)
        return render(request, 'payments/error.html', {'error': 'An error occurred'})
    

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('stripe-signature')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        #print("event", event)
        # Handle the event based on its type
        print("event type", event.type)
        if event.type == 'payment_intent.succeeded':
            print("payment intent succeeded")
            handle_payment_success(event.data.object)
        elif event.type == 'payment_intent.payment_failed':
            handle_payment_failure(event.data.object)
        elif event.type == 'payment_intent.requires_action':
            handle_payment_action_required(event.data.object)
        
        return HttpResponse(status=200)
        
    except stripe.error.SignatureVerificationError as e:
        #logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        #logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)
    

def handle_payment_success(payment_intent):
    """Handle successful payment"""
    try:
        # Get payment details
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        print("payment_intent", payment_intent)
        if not payment_link_id:
            #logger.error("Payment link ID not found in metadata")
            return
        try:   
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id)
        except PaymentLink.DoesNotExist:
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
        #logger.error(f"Error handling payment success: {str(e)}")
        print("payment success error", e)
        raise

def handle_payment_failure(payment_intent):
    """Handle failed payment"""
    try:
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        payment_link = PaymentLink.objects.get(unique_id=payment_link_id)
        payment_method_info = get_payment_method_details(payment_intent)

        if not payment_link_id:
            #logger.error("Payment link ID not found in metadata")
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
        print("payment failed")
        return HttpResponse(status=200)
        
    except Exception as e:
        print("payment failed error", e)
        #logger.error(f"Error handling payment failure: {str(e)}")
        raise

def handle_payment_action_required(payment_intent):
    """Handle payments requiring additional action"""
    try:
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
            
            
    except Exception as e:
        print("payment action required error", e)
        #logger.error(f"Error handling payment action required: {str(e)}")
        raise

