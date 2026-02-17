from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth import get_user_model

User = get_user_model()


def is_role(user, *roles):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or getattr(user, "role", None) in roles


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return is_role(request.user, User.Role.OWNER, User.Role.ADMIN)


class IsOwnerOrManager(BasePermission):
    def has_permission(self, request, view):
        return is_role(request.user, User.Role.OWNER, User.Role.MANAGER, User.Role.ADMIN)


class IsRestaurantReadWriteByStaff(BasePermission):
    """
    Auth required always.
    SAFE methods: OWNER/MANAGER/STAFF/VIEWER/ADMIN
    WRITE methods: OWNER/MANAGER/STAFF/ADMIN
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return is_role(
                user,
                User.Role.OWNER, User.Role.MANAGER, User.Role.STAFF, User.Role.VIEWER, User.Role.ADMIN
            )

        return is_role(
            user,
            User.Role.OWNER, User.Role.MANAGER, User.Role.STAFF, User.Role.ADMIN
        )
