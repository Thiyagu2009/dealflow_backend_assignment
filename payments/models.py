from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.crypto import get_random_string


class PaymentLink(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed')
    ]
    
    unique_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiration_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.unique_id}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = get_random_string(20)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('payment-page', args=[self.unique_id])


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ]
    
    payment_link = models.ForeignKey(PaymentLink, on_delete=models.CASCADE, related_name='payments')
    stripe_payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50)
    customer_email = models.EmailField(blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_disputed = models.BooleanField(default=False)
    dispute_reason = models.CharField(max_length=255, blank=True, null=True)
    dispute_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    dispute_created_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.stripe_payment_id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
