from datetime import datetime
from payments.models import PaymentLink
from rest_framework import serializers


class PaymentLinkSerializer(serializers.ModelSerializer):
    payment_url = serializers.SerializerMethodField()
    # Dynamic status field
    status = serializers.CharField(read_only=True)

    class Meta:
        model = PaymentLink
        fields = [
            'id', 
            'unique_id', 
            'amount', 
            'currency', 
            'description', 
            'status', 
            'created_at', 
            'updated_at',
            'expiration_date',
            'payment_url',
        ]
        read_only_fields = ['unique_id', 'status', 'payment_url','status']

    def get_payment_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.get_absolute_url())
        return obj.get_absolute_url()


class PaymentLinkCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    description = serializers.CharField(max_length=255)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    def validate_currency(self, value):
        valid_currencies = ['USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'CHF', 'JPY', 'NZD', 'SGD']  # Add more as needed
        if value.upper() not in valid_currencies:
            raise serializers.ValidationError(f"Currency must be one of {valid_currencies}")
        return value.upper()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
  
    def validate_expiration_date(self, value):
        if value and value < datetime.now().date():
            raise serializers.ValidationError("Expiration date cannot be in the past")
        return value
