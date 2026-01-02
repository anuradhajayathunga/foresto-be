from datetime import timedelta
from django.db.models import Sum
from inventory.models import Forecast, InventoryRecord

def get_current_stock(store, ingredient):
    return (
        InventoryRecord.objects
        .filter(store=store, ingredient=ingredient)
        .aggregate(total=Sum("quantity_on_hand"))["total"] or 0
    )

def get_forecast_demand(store, ingredient, days=7):
    start_date = Forecast.objects.filter(
        store=store,
        ingredient=ingredient
    ).earliest("forecast_date").forecast_date

    end_date = start_date + timedelta(days=days)

    return (
        Forecast.objects
        .filter(
            store=store,
            ingredient=ingredient,
            forecast_date__gte=start_date,
            forecast_date__lt=end_date
        )
        .aggregate(total=Sum("forecast_quantity"))["total"] or 0
    )

def compare_stock_vs_demand(stock, demand):
    return stock - demand
