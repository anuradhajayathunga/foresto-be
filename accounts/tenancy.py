from __future__ import annotations

from typing import Iterable, Optional, Tuple

from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import RestaurantMembership, Role

READ_ROLES = {
    Role.Names.OWNER,
    Role.Names.MANAGER,
    Role.Names.STAFF,
    Role.Names.VIEWER,
}
WRITE_ROLES = {
    Role.Names.OWNER,
    Role.Names.MANAGER,
    Role.Names.STAFF,
}
OWNER_ONLY = {Role.Names.OWNER}



def _parse_restaurant_id(raw_value: Optional[str]) -> Optional[int]:
    if raw_value in (None, ""):
        return None
    try:
        rid = int(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError({"restaurant_id": "X-Restaurant-ID must be an integer."}) from exc

    if rid <= 0:
        raise ValidationError({"restaurant_id": "X-Restaurant-ID must be a positive integer."})
    return rid



def get_request_restaurant_id(request, required: bool = True) -> Optional[int]:
    """
    Reads tenant context from request header/query params.

    Priority:
      1) X-Restaurant-ID header
      2) restaurant_id query param (fallback)
    """
    raw = request.headers.get("X-Restaurant-ID")
    if raw in (None, ""):
        raw = request.query_params.get("restaurant_id")

    restaurant_id = _parse_restaurant_id(raw)

    if required and restaurant_id is None:
        raise ValidationError(
            {"restaurant_id": "Missing tenant context. Send X-Restaurant-ID header."}
        )

    return restaurant_id



def get_active_membership(user, restaurant_id: int) -> Optional[RestaurantMembership]:
    if not user or not user.is_authenticated:
        return None

    return (
        RestaurantMembership.objects.select_related("role", "restaurant")
        .filter(
            user_id=user.id,
            restaurant_id=restaurant_id,
            is_active=True,
            restaurant__is_active=True,
        )
        .first()
    )



def assert_restaurant_access(
    request,
    allowed_roles: Optional[Iterable[str]] = None,
    required: bool = True,
) -> Tuple[Optional[int], Optional[RestaurantMembership]]:
    """
    Returns (restaurant_id, membership) if access is valid.
    Raises DRF exceptions otherwise.
    """
    restaurant_id = get_request_restaurant_id(request, required=required)

    if restaurant_id is None:
        return None, None

    if not request.user or not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")

    membership = get_active_membership(request.user, restaurant_id)
    if not membership:
        raise PermissionDenied("You are not an active member of this restaurant.")

    if allowed_roles and membership.role.name not in set(allowed_roles):
        raise PermissionDenied("Your role does not allow this action.")

    return restaurant_id, membership
