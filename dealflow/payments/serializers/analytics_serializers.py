from rest_framework import serializers
from datetime import datetime
from payments.models import Payment

class AnalyticsQueryParamsSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    start_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    end_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    payment_method = serializers.CharField(max_length=50, required=False)

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("End date must be after start date")
        return data

class PaymentMethodStatsSerializer(serializers.Serializer):
    payment_method = serializers.CharField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    success_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()

class CurrencyStatsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class DailyTransactionSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class StatusBreakdownSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class StatusBreakdownDetailSerializer(serializers.Serializer):
    success = StatusBreakdownSerializer()
    pending = StatusBreakdownSerializer()
    failed = StatusBreakdownSerializer()

class TotalPaymentsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class AnalyticsResponseSerializer(serializers.Serializer):
    total_payments = TotalPaymentsSerializer()
    status_breakdown = StatusBreakdownDetailSerializer()
    payment_methods = PaymentMethodStatsSerializer(many=True)
    currency_breakdown = CurrencyStatsSerializer(many=True)
    daily_transactions = DailyTransactionSerializer(many=True)