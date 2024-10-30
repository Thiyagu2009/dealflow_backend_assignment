import logging

from django.db.models import Sum, Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from payments.models import Payment, PaymentLink as PaymentLinkModel
from payments.serializers.analytics_serializers import (
    AnalyticsQueryParamsSerializer,
    PaymentMethodStatsSerializer,
    CurrencyStatsSerializer
)
from payments.serializers.payment_serializers import PaymentLinkSerializer
from dealflow.throttlers import AnalyticsUserThrottle


logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnalyticsUserThrottle])
def payment_analytics(request):
    """
    Get payment analytics with validated filters
    """
    # Validate query parameters
    logger.info(f"Received request for payment analytics: {request.GET}")
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
       
        analytics_data = payments.values('id','amount','currency','payment_method','status','created_at','payment_link__unique_id')
        return Response(analytics_data)

    except Exception as e:
        logger.error(f"Error fetching payment analytics: {str(e)}")
        return Response({
            "error": "Failed to fetch analytics",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnalyticsUserThrottle])
def payment_methods_summary(request):
    """
    Get validated summary of payment methods
    """
    try:
        logger.info(f"Received request for payment methods summary: {request.user}")
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
        logger.error(f"Error fetching payment methods summary: {str(e)}")
        return Response({
            "error": "Failed to fetch payment methods summary",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnalyticsUserThrottle])
def calculate_total_payments(request):
    """
    Get validated currency summary
    """
    try:
        logger.info(f"Received request for total payments: {request.user}")
        payments = Payment.objects.filter(payment_link__user=request.user, status='success')
        
        summary = payments.values('currency').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')

        # Validate response
        serializer = CurrencyStatsSerializer(data=list(summary), many=True)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.validated_data)

    except Exception as e:
        logger.error(f"Error fetching currency summary: {str(e)}")
        return Response({
            "error": "Failed to fetch currency summary",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnalyticsUserThrottle])
def payment_link_list(request):
    """
    List all payment links for the authenticated user
    """
    try:
        logger.info(f"Received request for payment links: {request.user}")
        payment_links = PaymentLinkModel.objects.filter(user=request.user).order_by('-created_at')
        serializer = PaymentLinkSerializer(
            payment_links, 
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching payment links: {str(e)}")
        return Response({
            "error": "Failed to fetch payment links",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})