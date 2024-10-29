import requests

from decimal import Decimal

from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def convert_to_usd(amount, currency):
    """Static method to convert amount to USD"""

    api_url = f'https://api.api-ninjas.com/v1/convertcurrency?have={currency}&want=USD&amount={amount}'
    response = requests.get(api_url, headers={'X-Api-Key': settings.API_NINJA_KEY})

    if response.status_code == requests.codes.ok:
        conversion_data = response.json()
        print(f"{conversion_data['old_amount']} {conversion_data['old_currency']} is equal to {conversion_data['new_amount']} {conversion_data['new_currency']}")
        return conversion_data['new_amount']
    else:
        print("Error:", response.status_code, response.text)
        return 0


def get_payment_method_details(payment_intent):
    """
    Extract payment method details from payment intent
    """
    try:
        # Get the payment method details
        if payment_intent.latest_charge:
            charge = stripe.Charge.retrieve(payment_intent.latest_charge)
            payment_method = charge.payment_method_details.type
            
            # Get additional details based on payment method type
            details = charge.payment_method_details.get(payment_method, {})
            
            return {
                'type': payment_method,
                'details': details,
                'brand': getattr(details, 'brand', None),
                'last4': getattr(details, 'last4', None),
            }
    except Exception as e:
        print("error getting payment method details", e)
        pass
        
    return {
        'type': 'unknown',
        'details': {}
    }