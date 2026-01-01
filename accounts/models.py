from django.contrib.auth.models import AbstractUser
from django.db import models

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
