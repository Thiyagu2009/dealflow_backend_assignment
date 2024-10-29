from rest_framework import serializers


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
    payment_method = serializers.CharField(allow_blank=True, required=False)
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    success_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()


class CurrencyStatsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
