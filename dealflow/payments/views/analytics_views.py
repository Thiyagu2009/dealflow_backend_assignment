from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from stripe import PaymentLink
from payments.models import PaymentLink as PaymentLinkModel
from payments.serializers.analytics_serializers import (
    AnalyticsQueryParamsSerializer,
    AnalyticsResponseSerializer,
    PaymentMethodStatsSerializer,
    CurrencyStatsSerializer
)
from payments.models import Payment
from payments.utils import convert_to_usd
from django.db.models import Q
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_analytics(request):
    """
    Get payment analytics with validated filters
    """
    # Validate query parameters
    query_serializer = AnalyticsQueryParamsSerializer(data=request.GET)
    if not query_serializer.is_valid():
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Base queryset
        payments = Payment.objects.filter(payment_link__user=request.user)
        # Apply validated filters
        validated_data = query_serializer.validated_data
        
        if validated_data.get('start_date'):
            payments = payments.filter(created_at__gte=validated_data['start_date'])
        if validated_data.get('end_date'):
            payments = payments.filter(created_at__lte=validated_data['end_date'])
        if validated_data.get('currency'):
            payments = payments.filter(currency=validated_data['currency'])
        if validated_data.get('payment_method'):
            payments = payments.filter(payment_method=validated_data['payment_method'])
        if validated_data.get('start_amount'):
            print(validated_data['start_amount'])
            payments = payments.filter(amount__gte=validated_data['start_amount'])
        if validated_data.get('end_amount'):
            payments = payments.filter(amount__lte=validated_data['end_amount'])
       
        analytics_data = payments.values('id','amount','currency','payment_method','status','created_at')
        
        
        return Response(analytics_data)

    except Exception as e:
        return Response({
            "error": "Failed to fetch analytics",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_methods_summary(request):
    """
    Get validated summary of payment methods
    """
    try:
        payments = Payment.objects.filter(payment_link__user=request.user)
        
        summary = payments.values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount'),
            success_count=Count('id', filter=Q(status='success')),
            failed_count=Count('id', filter=Q(status='failed'))
        ).order_by('-total_amount')

        # Validate response
        serializer = PaymentMethodStatsSerializer(data=list(summary), many=True)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.validated_data)

    except Exception as e:
        return Response({
            "error": "Failed to fetch payment methods summary",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def currency_summary(request):
    """
    Get validated currency summary
    """
    try:
        payments = Payment.objects.filter(payment_link__user=request.user)
        
        summary = payments.values('currency').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')

        # Validate response
        serializer = CurrencyStatsSerializer(data=list(summary), many=True)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.validated_data)

    except Exception as e:
        return Response({
            "error": "Failed to fetch currency summary",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_payments(request):
    """
    List payment links with their status
    """
    try:
        payment_links = PaymentLinkModel.objects.filter(user=request.user).values(
            'unique_id', 'amount', 'currency', 'status', 'description', 'created_at'
        )

        # Fetch payment status for each payment link
        payment_statuses = []
        for link in payment_links:
            payments = Payment.objects.filter(payment_link__unique_id=link['unique_id'])
            status_summary = payments.values('status','payment_method','created_at')
            payment_statuses.append({
                'payment_link': link,
                'status_summary': list(status_summary)
            })

        return Response(payment_statuses)

    except Exception as e:
        return Response({
            "error": "Failed to fetch payment links list with status",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_total_amount(request):
    """
    Calculate total amount of payments in USD
    """
    payments  = Payment.objects.filter(payment_link__user=request.user, status='success')
    total_amount = 0
    for payment in payments:
        print(payment.amount, payment.currency)
        total_amount += convert_to_usd(payment.amount, payment.currency)
    return Response({"total_amount": total_amount, "currency": "USD"})