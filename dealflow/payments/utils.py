

from decimal import Decimal

from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def convert_to_usd(amount, currency):
    """Static method to convert amount to USD"""
    if currency.upper() != "USD":
        amount = amount / 50 # Arbitrary rate
        print(amount)
    return amount

