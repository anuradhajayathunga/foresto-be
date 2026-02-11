from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Restaurant, RestaurantMembership, Role

User = get_user_model()

ROLE_DESCRIPTIONS = {
    Role.Names.OWNER: "Full control of a restaurant and its members.",
    Role.Names.MANAGER: "Operational management within assigned restaurant.",
    Role.Names.STAFF: "Day-to-day operations with limited write access.",
    Role.Names.VIEWER: "Read-only access to assigned restaurant data.",
}

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")


class RestaurantMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="role.name", read_only=True)
    restaurant_id = serializers.IntegerField(source="restaurant.id", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)

    class Meta:
        model = RestaurantMembership
        fields = (
            "id",
            "restaurant_id",
            "restaurant_name",
            "restaurant_slug",
            "user_id",
            "username",
            "email",
            "role",
            "is_active",
            "joined_at",
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    restaurant_name = serializers.CharField(write_only=True, min_length=2, max_length=150)
    restaurant = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "restaurant_name",
            "restaurant",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        restaurant_name = (attrs.get("restaurant_name") or "").strip()
        if not restaurant_name:
            raise serializers.ValidationError(
                {"restaurant_name": "Restaurant name is required."}
            )

        attrs["restaurant_name"] = restaurant_name
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        restaurant_name = validated_data.pop("restaurant_name")

        with transaction.atomic():
            user = User(**validated_data)
            # Safe default for public signup. Tenant privileges come from membership role.
            user.role = User.Role.STAFF
            user.set_password(password)
            user.save()

            restaurant = Restaurant.objects.create(
                name=restaurant_name,
                subscription_tier=Restaurant.SubscriptionTier.FREE,
                is_active=True,
            )

            owner_role, _ = Role.objects.get_or_create(
                name=Role.Names.OWNER,
                defaults={
                    "description": "Full control of a restaurant and its members."
                },
            )

            RestaurantMembership.objects.create(
                restaurant=restaurant,
                user=user,
                role=owner_role,
                is_active=True,
            )

            user._created_restaurant_id = restaurant.id

        return user

    def get_restaurant(self, obj):
        restaurant_id = getattr(obj, "_created_restaurant_id", None)

        membership_qs = obj.restaurant_memberships.select_related("restaurant", "role")
        if restaurant_id:
            membership = membership_qs.filter(
                restaurant_id=restaurant_id,
                is_active=True,
            ).first()
        else:
            membership = membership_qs.filter(
                role__name=Role.Names.OWNER,
                is_active=True,
            ).order_by("-joined_at").first()

        if not membership:
            return None

        return {
            "id": membership.restaurant.id,
            "name": membership.restaurant.name,
            "slug": membership.restaurant.slug,
            "role": membership.role.name,
        }


class MemberCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=[
            (Role.Names.MANAGER, "Manager"),
            (Role.Names.STAFF, "Staff"),
            (Role.Names.VIEWER, "Viewer"),
        ]
    )

    def validate_user_id(self, value):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User not found or inactive.")
        return value

    def create(self, validated_data):
        restaurant = self.context["restaurant"]
        role_name = validated_data["role"]
        user_id = validated_data["user_id"]

        role_obj = Role.objects.get(name=role_name)

        membership, created = RestaurantMembership.objects.get_or_create(
            restaurant=restaurant,
            user_id=user_id,
            defaults={"role": role_obj, "is_active": True},
        )

        if not created:
            membership.role = role_obj
            membership.is_active = True
            membership.save(update_fields=["role", "is_active"])

        return membership


class MemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            (Role.Names.MANAGER, "Manager"),
            (Role.Names.STAFF, "Staff"),
            (Role.Names.VIEWER, "Viewer"),
        ]
    )

    def update(self, instance, validated_data):
        role_obj = Role.objects.get(name=validated_data["role"])
        instance.role = role_obj
        instance.save(update_fields=["role"])
        return instance

    def create(self, validated_data):
        raise NotImplementedError


class StaffRegisterInRestaurantSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role = serializers.ChoiceField(
        choices=[Role.Names.MANAGER, Role.Names.STAFF, Role.Names.VIEWER],
        default=Role.Names.STAFF,
    )

    def validate(self, attrs):
        username = attrs["username"].strip()
        email = attrs["email"].strip().lower()
        attrs["username"] = username
        attrs["email"] = email

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({"username": "Username already exists."})

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        return attrs

    def create(self, validated_data):
        restaurant: Restaurant = self.context["restaurant"]
        role_name = validated_data.pop("role")

        role_obj, _ = Role.objects.get_or_create(
            name=role_name, defaults={"description": ROLE_DESCRIPTIONS.get(role_name, "")}
        )

        with transaction.atomic():
            user = User(
                username=validated_data["username"],
                email=validated_data["email"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                # IMPORTANT: platform role kept low; restaurant permissions come from membership role
                role=User.Role.STAFF,
                is_active=True,
            )
            user.set_password(validated_data["password"])
            try:
                user.save()
            except IntegrityError:
                raise serializers.ValidationError({"detail": "Username or email already exists."})

            membership = RestaurantMembership.objects.create(
                restaurant=restaurant,
                user=user,
                role=role_obj,
                is_active=True,
            )

        return membership


class MemberRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[Role.Names.MANAGER, Role.Names.STAFF, Role.Names.VIEWER])

    def update(self, instance: RestaurantMembership, validated_data):
        if instance.role.name == Role.Names.OWNER:
            raise serializers.ValidationError({"detail": "Owner membership cannot be changed."})

        role_name = validated_data["role"]
        role_obj, _ = Role.objects.get_or_create(
            name=role_name, defaults={"description": ROLE_DESCRIPTIONS.get(role_name, "")}
        )
        instance.role = role_obj
        instance.save(update_fields=["role"])
        return instance


class RestaurantMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = RestaurantMembership
        fields = ("id", "restaurant", "user_id", "username", "email", "role", "is_active", "joined_at")