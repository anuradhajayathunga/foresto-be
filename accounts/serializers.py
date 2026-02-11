from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Restaurant, RestaurantMembership, Role

User = get_user_model()

ROLE_DESCRIPTIONS = {
    Role.Names.OWNER: "Full control of a restaurant and its members.",
    Role.Names.MANAGER: "Operational management within assigned restaurant.",
    Role.Names.STAFF: "Day-to-day operations with limited write access.",
    Role.Names.VIEWER: "Read-only access to assigned restaurant data.",
}

ASSIGNABLE_ROLE_CHOICES = [
    (Role.Names.MANAGER, "Manager"),
    (Role.Names.STAFF, "Staff"),
    (Role.Names.VIEWER, "Viewer"),
]


def get_or_create_role(role_name: str) -> Role:
    role_name = str(role_name).upper()
    role, _ = Role.objects.get_or_create(
        name=role_name,
        defaults={"description": ROLE_DESCRIPTIONS.get(role_name, "")},
    )
    return role


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
    """
    Owner onboarding only:
    - create user
    - create restaurant
    - create OWNER membership
    """
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

        rn = (attrs.get("restaurant_name") or "").strip()
        if not rn:
            raise serializers.ValidationError({"restaurant_name": "Restaurant name is required."})
        attrs["restaurant_name"] = rn

        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        restaurant_name = validated_data.pop("restaurant_name")

        with transaction.atomic():
            user = User(**validated_data)
            # Platform safety: keep low platform privilege for public signup.
            user.role = User.Role.STAFF
            user.set_password(password)
            try:
                user.save()
            except IntegrityError:
                raise serializers.ValidationError({"detail": "Username or email already exists."})

            restaurant = Restaurant.objects.create(
                name=restaurant_name,
                subscription_tier=Restaurant.SubscriptionTier.FREE,
                is_active=True,
            )

            owner_role = get_or_create_role(Role.Names.OWNER)

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
        if not restaurant_id:
            return None

        membership = (
            obj.restaurant_memberships.select_related("restaurant", "role")
            .filter(restaurant_id=restaurant_id, is_active=True)
            .first()
        )
        if not membership:
            return None

        return {
            "id": membership.restaurant.id,
            "name": membership.restaurant.name,
            "slug": membership.restaurant.slug,
            "role": membership.role.name,
        }


class MemberCreateSerializer(serializers.Serializer):
    """
    Supports 2 modes:
    1) Existing user:
       { "user_id": 12, "role": "STAFF" }

    2) Create new user + membership:
       {
         "username": "newstaff",
         "email": "newstaff@example.com",
         "password": "StrongPass123!",
         "first_name": "New",
         "last_name": "Staff",
         "role": "STAFF"
       }
    """
    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLE_CHOICES)

    # existing user mode
    user_id = serializers.IntegerField(required=False)

    # new user mode
    username = serializers.CharField(required=False, min_length=3, max_length=150)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, min_length=8, max_length=128, write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate(self, attrs):
        restaurant: Restaurant = self.context["restaurant"]

        has_user_id = attrs.get("user_id") is not None
        has_new_fields = any(attrs.get(k) for k in ("username", "email", "password"))

        if has_user_id and has_new_fields:
            raise serializers.ValidationError(
                "Provide either user_id OR username/email/password, not both."
            )

        if not has_user_id and not has_new_fields:
            raise serializers.ValidationError(
                "Provide user_id OR username/email/password."
            )

        if has_user_id:
            user = User.objects.filter(id=attrs["user_id"], is_active=True).first()
            if not user:
                raise serializers.ValidationError({"user_id": "User not found or inactive."})

            existing = (
                RestaurantMembership.objects.select_related("role")
                .filter(restaurant=restaurant, user=user)
                .first()
            )
            if existing and existing.role.name == Role.Names.OWNER:
                raise serializers.ValidationError({"detail": "Owner membership cannot be changed here."})

            attrs["_mode"] = "existing"
            attrs["_user"] = user
            attrs["_existing"] = existing
            return attrs

        # new user mode
        required = ("username", "email", "password")
        missing = [k for k in required if not attrs.get(k)]
        if missing:
            raise serializers.ValidationError(
                {"detail": f"Missing fields for new user mode: {', '.join(missing)}"}
            )

        username = attrs["username"].strip()
        email = attrs["email"].strip().lower()
        attrs["username"] = username
        attrs["email"] = email

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        attrs["_mode"] = "new"
        return attrs

    def create(self, validated_data):
        restaurant: Restaurant = self.context["restaurant"]
        role_obj = get_or_create_role(validated_data["role"])

        with transaction.atomic():
            if validated_data["_mode"] == "existing":
                user = validated_data["_user"]
                existing = validated_data["_existing"]

                if existing:
                    existing.role = role_obj
                    existing.is_active = True
                    existing.save(update_fields=["role", "is_active"])
                    return existing

                return RestaurantMembership.objects.create(
                    restaurant=restaurant,
                    user=user,
                    role=role_obj,
                    is_active=True,
                )

            # create new user + membership
            user = User(
                username=validated_data["username"],
                email=validated_data["email"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                role=User.Role.STAFF,  # low platform privilege
                is_active=True,
            )
            user.set_password(validated_data["password"])
            try:
                user.save()
            except IntegrityError:
                raise serializers.ValidationError({"detail": "Username or email already exists."})

            return RestaurantMembership.objects.create(
                restaurant=restaurant,
                user=user,
                role=role_obj,
                is_active=True,
            )


class MemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required: role or is_active.")

        instance: RestaurantMembership = self.instance
        if instance and instance.role.name == Role.Names.OWNER:
            raise serializers.ValidationError({"detail": "Owner membership cannot be modified."})

        return attrs

    def update(self, instance: RestaurantMembership, validated_data):
        update_fields = []

        if "role" in validated_data:
            instance.role = get_or_create_role(validated_data["role"])
            update_fields.append("role")

        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]
            update_fields.append("is_active")

        if update_fields:
            instance.save(update_fields=update_fields)

        return instance

    def create(self, validated_data):
        raise NotImplementedError
