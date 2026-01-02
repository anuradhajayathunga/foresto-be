from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone
from inventory.models import Forecast


def get_forecast_demand(store, ingredient, days=7):
    today = timezone.now().date()
    end_date = today + timedelta(days=days)

    return (
        Forecast.objects.filter(
            store=store,
            ingredient=ingredient,
            forecast_date__gte=today,
            forecast_date__lt=end_date,
        )
        .aggregate(total=Sum("forecast_quantity"))["total"]
        or 0
    )
