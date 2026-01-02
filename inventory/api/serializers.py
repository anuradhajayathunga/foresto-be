from rest_framework import serializers

class AutoPORequestSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    days = serializers.IntegerField(default=7)
