from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.tenancy import READ_ROLES, assert_restaurant_access

from .services import predict_menu_demand
from .services_history import predict_past_days
from .services_ingredients import build_ingredient_plan


class ForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant_id, _ = assert_restaurant_access(request, allowed_roles=READ_ROLES)

        horizon = int(request.query_params.get("horizon", "7"))
        horizon = max(1, min(horizon, 30))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        data = predict_menu_demand(
            horizon_days=horizon,
            top_n=top_n,
            restaurant_id=restaurant_id,
        )
        return Response(data)


class ForecastHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant_id, _ = assert_restaurant_access(request, allowed_roles=READ_ROLES)

        days = int(request.query_params.get("days", "14"))
        days = max(1, min(days, 90))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        data = predict_past_days(
            days=days,
            top_n=top_n,
            restaurant_id=restaurant_id,
        )
        return Response(data)


class ForecastIngredientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant_id, _ = assert_restaurant_access(request, allowed_roles=READ_ROLES)

        scope = (request.query_params.get("scope") or "next7").strip().lower()
        if scope not in ("tomorrow", "next7"):
            scope = "next7"

        horizon = int(request.query_params.get("horizon", "7"))
        horizon = max(1, min(horizon, 30))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        data = build_ingredient_plan(
            horizon_days=horizon,
            top_n_items=top_n,
            scope=scope,
            restaurant_id=restaurant_id,
        )
        return Response(data)
