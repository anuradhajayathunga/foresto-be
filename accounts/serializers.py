from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Restaurant
import re

User = get_user_model()


def generate_username_from_email(email):
    """Generate a unique username from email address."""
    # Extract the part before @ symbol
    username = email.split('@')[0]
    # Remove any non-alphanumeric characters except underscore and dot
    username = re.sub(r'[^a-zA-Z0-9_.]', '', username)
    # Ensure it's not empty and has valid length
    if not username:
        username = 'user'
    
    # Ensure username doesn't exceed max length
    username = username[:150]
    
    # Check if username already exists, if so append numbers
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        suffix = str(counter)
        # Ensure total length doesn't exceed 150
        max_base_len = 150 - len(suffix) - 1
        username = f"{base_username[:max_base_len]}{suffix}"
        counter += 1
    
    return username


class UserSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "role", "restaurant", "restaurant_name", "is_active"
        )


class RegisterOwnerSerializer(serializers.Serializer):
    restaurant_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        # Auto-generate username if not provided
        username = attrs.get("username", "").strip()
        if not username:
            attrs["username"] = generate_username_from_email(attrs["email"])
        else:
            # Validate provided username
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "Username already exists."})
        
        return attrs

    def create(self, validated_data):
        restaurant_name = (validated_data.pop("restaurant_name", "") or "").strip()
        username = validated_data.get("username", "")
        
        if not restaurant_name:
            # Use email if username is not available for restaurant name
            if username:
                restaurant_name = f"{username}'s Restaurant"
            else:
                email_part = validated_data["email"].split('@')[0]
                restaurant_name = f"{email_part}'s Restaurant"

        validated_data.pop("password2")
        password = validated_data.pop("password")

        restaurant = Restaurant.objects.create(name=restaurant_name)

        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=User.Role.OWNER,
            restaurant=restaurant,
            is_active=True,
        )
        user.set_password(password)
        user.save()
        return user

class RestaurantDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "subscription_tier",
            "created_at",
            "updated_at",
        ]

class TeamUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role = serializers.ChoiceField(choices=[User.Role.MANAGER, User.Role.STAFF, User.Role.VIEWER])

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        # Auto-generate username if not provided
        username = attrs.get("username", "").strip()
        if not username:
            attrs["username"] = generate_username_from_email(attrs["email"])
        else:
            # Validate provided username
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "Username already exists."})
        
        return attrs

    def create(self, validated_data):
        owner = self.context["request"].user

        validated_data.pop("password2")
        password = validated_data.pop("password")

        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data["role"],
            restaurant=owner.restaurant,
            is_active=True,
        )
        user.set_password(password)
        user.save()
        return user


class TeamUserUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[User.Role.MANAGER, User.Role.STAFF, User.Role.VIEWER])

    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "is_active")