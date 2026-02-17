from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.permissions import IsStaff
from .services import predict_menu_demand
from .services_history import predict_past_days
from .services_ingredients import build_ingredient_plan


class DemandForecastView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        horizon = int(request.query_params.get("horizon_days", "7"))
        horizon = max(1, min(horizon, 30))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        restaurant_id = None if request.user.is_superuser else getattr(request.user, "restaurant_id", None)
        if not request.user.is_superuser and not restaurant_id:
            return Response({"detail": "User has no restaurant assigned."}, status=400)

        data = predict_menu_demand(horizon_days=horizon, top_n=top_n, restaurant_id=restaurant_id)
        return Response(data)


class ForecastHistoryView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        days = int(request.query_params.get("days", "14"))
        top_n = int(request.query_params.get("top_n", "50"))

        restaurant_id = None if request.user.is_superuser else getattr(request.user, "restaurant_id", None)
        if not request.user.is_superuser and not restaurant_id:
            return Response({"detail": "User has no restaurant assigned."}, status=400)

        data = predict_past_days(days=days, top_n=top_n, restaurant_id=restaurant_id)
        return Response(data)


class IngredientPlanView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        horizon = int(request.query_params.get("horizon_days", "7"))
        horizon = max(1, min(horizon, 30))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        scope = (request.query_params.get("scope", "next7") or "next7").lower()
        if scope not in ("tomorrow", "next7"):
            scope = "next7"

        restaurant_id = None if request.user.is_superuser else getattr(request.user, "restaurant_id", None)
        if not request.user.is_superuser and not restaurant_id:
            return Response({"detail": "User has no restaurant assigned."}, status=400)

        data = build_ingredient_plan(
            horizon_days=horizon,
            top_n_items=top_n,
            scope=scope,
            restaurant_id=restaurant_id,
        )
        return Response(data)
