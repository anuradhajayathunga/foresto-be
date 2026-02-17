from django.contrib.auth import get_user_model
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import Restaurant

from .serializers import (
    RegisterOwnerSerializer,
    RestaurantDetailSerializer,
    UserSerializer,
    TeamUserCreateSerializer,
    TeamUserUpdateSerializer,
)
from .permissions import IsOwner, IsOwnerOrManager

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Owner sign-up endpoint:
    creates restaurant + owner account
    """
    serializer_class = RegisterOwnerSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
    
class MyRestaurantsView(APIView):
    """
    GET y-restaurants/  -> current user's restaurant details
    Optional: superuser can get all with ?all=1
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Optional: admin mode
        if user.is_superuser and request.query_params.get("all") == "1":
            qs = Restaurant.objects.filter(is_active=True).order_by("name")
            data = RestaurantDetailSerializer(qs, many=True).data
            return Response(data, status=status.HTTP_200_OK)

        # Normal user: return assigned restaurant only
        if not getattr(user, "restaurant_id", None):
            return Response(
                {"detail": "No restaurant assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = RestaurantDetailSerializer(user.restaurant).data
        return Response(data, status=status.HTTP_200_OK)


class TeamUserViewSet(viewsets.ModelViewSet):
    """
    Owner manages users in their own restaurant.
    """
    queryset = User.objects.none()
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        u = self.request.user
        if u.is_superuser:
            return User.objects.all().order_by("id")
        if not u.restaurant_id:
            return User.objects.none()
        return User.objects.filter(restaurant_id=u.restaurant_id).order_by("id")

    def get_serializer_class(self):
        if self.action == "create":
            return TeamUserCreateSerializer
        if self.action in ["partial_update", "update"]:
            return TeamUserUpdateSerializer
        return UserSerializer

    def _ensure_owner(self):
        u = self.request.user
        if not (u.is_superuser or u.role in [User.Role.OWNER, User.Role.ADMIN]):
            raise PermissionDenied("Only owner can manage team users.")

    def list(self, request, *args, **kwargs):
        # owner or manager can list
        if not (request.user.is_superuser or request.user.role in [User.Role.OWNER, User.Role.ADMIN, User.Role.MANAGER]):
            raise PermissionDenied("Only owner/manager can view team users.")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role in [User.Role.OWNER, User.Role.ADMIN, User.Role.MANAGER]):
            raise PermissionDenied("Only owner/manager can view team users.")
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._ensure_owner()
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._ensure_owner()
        target = self.get_object()
        if target.role == User.Role.OWNER and not request.user.is_superuser:
            raise ValidationError({"detail": "Cannot edit OWNER via this endpoint."})
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._ensure_owner()
        target = self.get_object()
        if target.role == User.Role.OWNER:
            raise ValidationError({"detail": "Cannot delete OWNER account."})

        # soft delete
        target.is_active = False
        target.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
