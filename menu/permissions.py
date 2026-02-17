from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # supports either role field or is_staff
        return getattr(user, "is_staff", False) or getattr(user, "role", "") in ["ADMIN", "MANAGER","OWNER"]
