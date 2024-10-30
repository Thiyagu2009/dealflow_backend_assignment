from unittest.mock import patch, MagicMock
import json
import stripe
from django.test import TestCase, Client
from django.urls import reverse
from payments.models import Payment, PaymentLink
from django.contrib.auth import get_user_model

User = get_user_model()

class StripeWebhookTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('stripe-webhook')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.payment_link = PaymentLink.objects.create(
            unique_id='test_link_123',
            amount=1000,  # $10.00
            currency='USD',
            user=self.user
        )
        
        # Mock stripe signature verification
        self.stripe_construct_patcher = patch('stripe.Webhook.construct_event')
        self.mock_construct_event = self.stripe_construct_patcher.start()

        # Mock get_payment_method_details
        self.get_payment_details_patcher = patch('payments.views.stripe_webhooks.get_payment_method_details')
        self.mock_get_payment_details = self.get_payment_details_patcher.start()

    def tearDown(self):
        self.stripe_construct_patcher.stop()
        self.get_payment_details_patcher.stop()

    def test_payment_intent_succeeded(self):
        # Set up payment method details mock
        self.mock_get_payment_details.return_value = {
            'type': 'card',
            'details': {
                'card': {
                    'brand': 'visa',
                    'last4': '4242'
                }
            }
        }

        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_123'
        mock_payment_intent.amount = 1000
        mock_payment_intent.currency = 'usd'
        mock_payment_intent.payment_method = 'pm_123'
        mock_payment_intent.customer = 'cus_123'
        mock_payment_intent.metadata = {
            'payment_link_id': self.payment_link.unique_id,
            'payment_method_type': 'card'
        }

        # Mock the Stripe event
        mock_event = MagicMock()
        mock_event.type = 'payment_intent.succeeded'
        mock_event.data.object = mock_payment_intent
        self.mock_construct_event.return_value = mock_event

        response = self.client.post(
            self.webhook_url,
            data={},
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='dummy_sig'
        )

        self.assertEqual(response.status_code, 200)

        # Assert payment was created
        payment = Payment.objects.get(stripe_payment_id='pi_123')
        self.assertEqual(payment.status, 'success')
        self.assertEqual(payment.amount, 10.00)
        self.assertEqual(payment.currency, 'USD')
        self.assertEqual(payment.payment_method, 'card')

    
    def test_invalid_signature(self):
        # Mock signature verification failure
        self.mock_construct_event.side_effect = stripe.error.SignatureVerificationError('Invalid signature', None)

        response = self.client.post(
            self.webhook_url,
            data={},
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_sig'
        )

        self.assertEqual(response.status_code, 400)

    def test_payment_action_required(self):
        # Create mock payment intent
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_123_pending'
        mock_payment_intent.amount = 1000
        mock_payment_intent.currency = 'usd'
        mock_payment_intent.metadata = {'payment_link_id': self.payment_link.unique_id}

        # Mock the Stripe event
        mock_event = MagicMock()
        mock_event.type = 'payment_intent.requires_action'
        mock_event.data.object = mock_payment_intent
        self.mock_construct_event.return_value = mock_event

        response = self.client.post(
            self.webhook_url,
            data={},
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='dummy_sig'
        )

        self.assertEqual(response.status_code, 200)

        # Assert pending payment was created
        payment = Payment.objects.get(stripe_payment_id='pi_123_pending')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, 10.00)
        self.assertEqual(payment.currency, 'USD')