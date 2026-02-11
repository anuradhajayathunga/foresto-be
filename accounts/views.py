from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Restaurant, RestaurantMembership, Role
from .serializers import (
    MemberCreateSerializer,
    MemberUpdateSerializer,
    RegisterSerializer,
    RestaurantMembershipSerializer,
    UserSerializer,
    StaffRegisterInRestaurantSerializer,
    MemberRoleUpdateSerializer,
)
from .tenancy import OWNER_ONLY, assert_restaurant_access


from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class MyRestaurantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            RestaurantMembership.objects.select_related("restaurant", "role")
            .filter(user=request.user, is_active=True, restaurant__is_active=True)
            .order_by("restaurant__name")
        )
        data = RestaurantMembershipSerializer(memberships, many=True).data
        return Response(data)


class RestaurantMembersView(APIView):
    """
    GET  /api/auth/restaurants/<restaurant_id>/members/
    POST /api/auth/restaurants/<restaurant_id>/members/

    Owner only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, restaurant_id: int):
        self._ensure_owner_access(request, restaurant_id)

        members = (
            RestaurantMembership.objects.select_related("user", "role", "restaurant")
            .filter(restaurant_id=restaurant_id)
            .order_by("-is_active", "role__name", "user__username")
        )
        return Response(RestaurantMembershipSerializer(members, many=True).data)

    def post(self, request, restaurant_id: int):
        restaurant = self._ensure_owner_access(request, restaurant_id)
        serializer = MemberCreateSerializer(data=request.data, context={"restaurant": restaurant})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(
            RestaurantMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    def _ensure_owner_access(self, request, restaurant_id: int) -> Restaurant:
        header_restaurant_id = request.headers.get("X-Restaurant-ID")
        if not header_restaurant_id:
            request.META["HTTP_X_RESTAURANT_ID"] = str(restaurant_id)

        restaurant_id_from_context, _membership = assert_restaurant_access(
            request,
            allowed_roles=OWNER_ONLY,
        )
        restaurant = get_object_or_404(Restaurant, id=restaurant_id_from_context, is_active=True)
        return restaurant


class RestaurantMemberDetailView(APIView):
    """
    PATCH  /api/auth/restaurants/<restaurant_id>/members/<membership_id>/
    DELETE /api/auth/restaurants/<restaurant_id>/members/<membership_id>/

    Owner only.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, restaurant_id: int, membership_id: int):
        self._ensure_owner_access(request, restaurant_id)

        membership = get_object_or_404(
            RestaurantMembership.objects.select_related("role", "user", "restaurant"),
            id=membership_id,
            restaurant_id=restaurant_id,
        )

        if membership.role.name == Role.Names.OWNER:
            return Response(
                {"detail": "Owner role cannot be changed from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = serializer.update(membership, serializer.validated_data)

        return Response(RestaurantMembershipSerializer(membership).data)

    def delete(self, request, restaurant_id: int, membership_id: int):
        self._ensure_owner_access(request, restaurant_id)

        membership = get_object_or_404(
            RestaurantMembership.objects.select_related("role", "user", "restaurant"),
            id=membership_id,
            restaurant_id=restaurant_id,
        )

        if membership.role.name == Role.Names.OWNER:
            return Response(
                {"detail": "Owner membership cannot be removed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _ensure_owner_access(self, request, restaurant_id: int) -> None:
        header_restaurant_id = request.headers.get("X-Restaurant-ID")
        if not header_restaurant_id:
            request.META["HTTP_X_RESTAURANT_ID"] = str(restaurant_id)

        assert_restaurant_access(request, allowed_roles=OWNER_ONLY)
    

def _assert_owner(user, restaurant_id: int):
    is_owner = RestaurantMembership.objects.filter(
        restaurant_id=restaurant_id,
        user=user,
        is_active=True,
        role__name=Role.Names.OWNER,
    ).exists()
    if not is_owner:
        raise PermissionDenied("Only restaurant owners can perform this action.")


class RestaurantStaffRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, restaurant_id: int):
        _assert_owner(request.user, restaurant_id)

        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)

        serializer = StaffRegisterInRestaurantSerializer(
            data=request.data,
            context={"restaurant": restaurant, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return Response(RestaurantMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class RestaurantMemberRoleUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, restaurant_id: int, membership_id: int):
        _assert_owner(request.user, restaurant_id)

        membership = get_object_or_404(
            RestaurantMembership.objects.select_related("role"),
            id=membership_id,
            restaurant_id=restaurant_id,
            is_active=True,
        )

        serializer = MemberRoleUpdateSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        return Response(RestaurantMembershipSerializer(updated).data, status=status.HTTP_200_OK)
