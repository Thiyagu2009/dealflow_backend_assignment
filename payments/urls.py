from django.urls import path
from .views import payment_views, analytics_views

urlpatterns = [
    path('payment-links/create/', payment_views.create_payment_link, name='create-payment-link'),
    path('payment/<str:payment_id>/create-intent/', payment_views.create_payment_intent, name='create-payment-intent'),
    path('analytics/', analytics_views.payment_analytics, name='payment-analytics'),
    path('analytics/payment-methods/', analytics_views.payment_methods_summary, 
         name='payment-methods-summary'),
    path('analytics/payments/total/', analytics_views.calculate_total_payments, 
         name='currency-summary'),
    path('analytics/payment-links/', analytics_views.payment_link_list, 
         name='list-payment-links'),
   
]