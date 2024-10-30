from datetime import datetime, timedelta
import stripe
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class PaymentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.access_token}'
        
        self.payment_data = {
            'amount': '100.00',
            'currency': 'USD',
            'description': 'Test payment',
            'expiration_date': (datetime.now() + timedelta(days=7)).date().isoformat()
        }

    def test_payment_analytics_authenticated(self):
        """Test accessing payment analytics"""
        response = self.client.get(
            reverse('payment-analytics'),
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, 200)

    def test_payment_methods_summary_authenticated(self):
        """Test accessing payment methods summary"""
        response = self.client.get(
            reverse('payment-methods-summary'),
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, 200)

    def test_calculate_total_payments_authenticated(self):
        """Test accessing total payments summary"""
        response = self.client.get(
            reverse('currency-summary'),
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, 200)

    def test_payment_link_list_authenticated(self):
        """Test accessing payment links list"""
        response = self.client.get(
            reverse('list-payment-links'),
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, 200)

    def test_payment_analytics_unauthenticated(self):
        """Test accessing payment analytics without authentication"""
        client = Client()  # New client without auth
        response = client.get(reverse('payment-analytics'))
        self.assertEqual(response.status_code, 401)

    def test_create_payment_link_authenticated(self):
        """Test creating payment link with authenticated user"""
        response = self.client.post(
            reverse('create-payment-link'),
            data=self.payment_data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue('payment_url' in response.json())
        self.assertTrue('payment_id' in response.json())

    def test_create_payment_link_unauthenticated(self):
        """Test creating payment link without authentication"""
        client = Client()  # New client without auth
        response = client.post(
            reverse('create-payment-link'),
            data=self.payment_data,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)