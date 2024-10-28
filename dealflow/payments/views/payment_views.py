from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import stripe
from payments.utils import convert_to_usd
from payments.models import Payment, PaymentLink
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.http import require_http_methods

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_link(request):
    try:
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        description = request.data.get('description', '')
        expiration_date = request.data.get('expiration_date')

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

def payment_page(request, payment_id):
    try:
        payment_link = get_object_or_404(PaymentLink, unique_id=payment_id)
        print("expiration date", payment_link.expiration_date)
        if payment_link.expiration_date and payment_link.expiration_date < datetime.now().date():
            payment_link.status = 'expired'
            payment_link.save()
            return render(request, 'payments/error.html', {'error': 'Payment link expired'})
        if payment_link.status == 'completed':
            return render(request, 'payments/payment_completed.html')     
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
def create_payment_intent(request, payment_id):
    try:
        # Find payment link
        payment_link = get_object_or_404(PaymentLink, unique_id=payment_id)
        
        print(payment_link.amount, payment_link.currency.lower())
        # Create payment intent
        intent =stripe.PaymentIntent.create(
            amount=int(float(payment_link.amount) * 100),  # Convert to cents
            currency=payment_link.currency.lower(),
            automatic_payment_methods={
                'enabled': True
            },
            metadata={
                'payment_link_id': payment_link.unique_id
            }
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
@require_http_methods(["GET"])
def payment_success(request):
    payment_intent_id = request.GET.get('payment_intent')
    try:
        # Retrieve the payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Get the payment link ID from metadata
        payment_link_id = payment_intent.metadata.get('payment_link_id')
        
        if payment_link_id:
            payment_link = PaymentLink.objects.get(unique_id=payment_link_id, status="active")
            
            # Create or update payment record
            Payment.objects.create(
                payment_link=payment_link,
                stripe_payment_id=payment_intent_id,
                amount=payment_intent.amount / 100,  # Convert from cents
                currency=payment_intent.currency.upper(),
                status='success',
                payment_method=payment_intent.payment_method_types[0],
                usd_amount=convert_to_usd(payment_intent.amount , payment_intent.currency.upper())
            )
            payment_link.status = 'completed'
            payment_link.save()
            
            return render(request, 'payments/success.html', {
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency.upper(),
            })
        
    except stripe.error.StripeError as e:
        return render(request, 'payments/error.html', {'error': str(e)})
    except PaymentLink.DoesNotExist:
        return render(request, 'payments/error.html', {'error': 'Payment not found'})
    except Exception as e:
        return render(request, 'payments/error.html', {'error': 'An error occurred'})