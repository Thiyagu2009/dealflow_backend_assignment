from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class AnalyticsUserThrottle(UserRateThrottle):
    rate = '1000/hour'


class PaymentUserThrottle(UserRateThrottle):
    rate = '1000/hour'


class PaymentAnonThrottle(AnonRateThrottle):
    rate = '400/hour'
