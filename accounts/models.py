from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class Restaurant(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[
            ('FREE', 'Free'),
            ('PRO', 'Pro'),
            ('ENTERPRISE', 'Enterprise'),
        ],
        default='FREE'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "restaurant"
            candidate = base
            n = 2
            while Restaurant.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{n}"
                n += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"
        VIEWER = "VIEWER", "Viewer"
        ADMIN = "ADMIN", "Admin"  

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)

    # nullable first for safe migration
    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        # Global admin
        if self.is_superuser or self.role == self.Role.ADMIN:
            self.role = self.Role.ADMIN
            self.is_superuser = True
            self.is_staff = True
        else:
            self.is_superuser = False
            # Keep Django admin access for internal roles if you want
            self.is_staff = self.role in {self.Role.OWNER, self.Role.MANAGER, self.Role.STAFF}

        super().save(*args, **kwargs)
