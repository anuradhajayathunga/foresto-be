from django.core.exceptions import FieldError


class RestaurantScopedQuerysetMixin:
    """
    Scopes queryset to authenticated user's restaurant.
    Set restaurant_lookup for nested lookups (e.g. "menu_item__restaurant", "item__restaurant").
    """
    restaurant_lookup = "restaurant"

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)

        if not user or not user.is_authenticated:
            return qs.none()

        # platform superuser can see all
        if user.is_superuser:
            return qs

        restaurant_id = getattr(user, "restaurant_id", None)
        if not restaurant_id:
            return qs.none()

        try:
            return qs.filter(**{f"{self.restaurant_lookup}_id": restaurant_id})
        except FieldError:
            # safety fallback if a model doesn't have the expected relation yet
            return qs.none()

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        model = getattr(getattr(serializer, "Meta", None), "model", None)

        if model and any(f.name == "restaurant" for f in model._meta.fields):
            if user and user.is_authenticated and getattr(user, "restaurant_id", None):
                serializer.save(restaurant_id=user.restaurant_id)
                return

        serializer.save()
