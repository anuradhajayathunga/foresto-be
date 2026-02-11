from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"
        MANAGER = "MANAGER", "Manager"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)

    def save(self, *args, **kwargs):
        # keep permissions consistent with role
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_staff = True
        else:
            if self.role == self.Role.STAFF:
                self.is_staff = True
                self.is_superuser = False
            elif self.role == self.Role.MANAGER:
                self.is_staff = True
                self.is_superuser = True
            elif self.role == self.Role.ADMIN:
                self.is_staff = True
                self.is_superuser = True

        super().save(*args, **kwargs)


class Restaurant(models.Model):
    """Multi-tenant restaurant entity."""

    class SubscriptionTier(models.TextChoices):
        FREE = "FREE", "Free"
        PRO = "PRO", "Pro"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "restaurants"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["-created_at"]

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)[:140] or "restaurant"
        candidate = base_slug
        suffix = 2

        while (
            Restaurant.objects.filter(slug=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            suffix_str = f"-{suffix}"
            candidate = f"{base_slug[:150 - len(suffix_str)]}{suffix_str}"
            suffix += 1

        return candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Role(models.Model):
    """User roles for restaurant-level RBAC."""

    class Names(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"
        VIEWER = "VIEWER", "Viewer"

    name = models.CharField(max_length=20, choices=Names.choices, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class RestaurantMembership(models.Model):
    """Maps users to restaurants with one restaurant-level role per membership."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurant_memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "restaurant_memberships"
        unique_together = ("restaurant", "user")
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user_id}::{self.restaurant_id}::{self.role.name}"
