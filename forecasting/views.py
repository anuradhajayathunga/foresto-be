# forecasting/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from inventory.permissions import IsStaff
from .services import predict_menu_demand

class DemandForecastView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        horizon = int(request.query_params.get("horizon_days", "7"))
        horizon = max(1, min(horizon, 30))

        top_n = int(request.query_params.get("top_n", "50"))
        top_n = max(1, min(top_n, 500))

        data = predict_menu_demand(horizon_days=horizon, top_n=top_n)
        return Response(data)
