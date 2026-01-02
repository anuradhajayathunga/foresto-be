from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from inventory.models import Store
from inventory.services.purchase_order import generate_batch_smart_pos


class AutoPOView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store_id = request.data.get("store_id")
        days = int(request.data.get("days", 7))

        if not store_id:
            return Response(
                {"error": "store_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response(
                {"error": "Store not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        pos = generate_batch_smart_pos(store, days=days)

        return Response(
            {
                "purchase_orders": [
                    {
                        "id": po.id,
                        "supplier": po.supplier.name,
                        "items": [
                            {
                                "ingredient": item.ingredient.name,
                                "quantity": item.ordered_quantity,
                            }
                            for item in po.items.all()
                        ],
                    }
                    for po in pos
                ]
            },
            status=status.HTTP_201_CREATED
        )
