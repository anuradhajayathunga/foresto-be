from rest_framework import serializers
from .models import Account


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'username', 'email', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Account.objects.create_user(**validated_data, password=password)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'first_name', 'last_name', 'username', 'email']
