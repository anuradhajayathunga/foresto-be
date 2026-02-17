from datetime import timedelta

import pandas as pd
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from menu.models import MenuItem
from sales.models import Sale, SaleItem
from .ml import get_model

FEATURES = ["day_of_week", "month", "is_weekend", "lag_1", "lag_7", "rolling_mean_7"]


def _daily_qty_map(days_back: int = 120, restaurant_id=None):
    """
    Returns dict: {menu_item_id: {date: qty}}
    Uses PAID only.
    """
    today = timezone.localdate()
    start = today - timedelta(days=days_back - 1)

    sale_fields = {f.name for f in Sale._meta.fields}
    date_field = "sale__sold_at" if "sold_at" in sale_fields else "sale__created_at"

    qs = (
        SaleItem.objects.filter(sale__status="PAID", menu_item__isnull=False)
        .annotate(day=TruncDate(date_field))
        .filter(day__gte=start, day__lte=today)
    )

    if restaurant_id is not None:
        qs = qs.filter(
            sale__restaurant_id=restaurant_id,
            menu_item__restaurant_id=restaurant_id,
        )

    qs = (
        qs.values("menu_item_id", "day")
        .annotate(qty=Sum("qty"))
        .order_by("menu_item_id", "day")
    )

    out = {}
    for r in qs:
        out.setdefault(r["menu_item_id"], {})[r["day"]] = float(r["qty"] or 0)
    return start, today, out


def _rolling_mean_7(series: dict, day):
    vals = [float(series.get(day - timedelta(days=i), 0)) for i in range(1, 8)]
    return sum(vals) / 7.0


def _feature_row(day, series):
    dow = day.weekday()
    return {
        "day_of_week": dow,
        "month": day.month,
        "is_weekend": 1 if dow >= 5 else 0,
        "lag_1": float(series.get(day - timedelta(days=1), 0)),
        "lag_7": float(series.get(day - timedelta(days=7), 0)),
        "rolling_mean_7": _rolling_mean_7(series, day),
    }


def predict_menu_demand(horizon_days=7, days_back=120, top_n=50, restaurant_id=None):
    model = get_model()

    start, today, qty_map = _daily_qty_map(days_back=days_back, restaurant_id=restaurant_id)
    tomorrow = today + timedelta(days=1)
    future_days = [tomorrow + timedelta(days=i) for i in range(horizon_days)]

    item_ids = list(qty_map.keys())
    if not item_ids:
        mi_qs = MenuItem.objects.all()
        if restaurant_id is not None:
            mi_qs = mi_qs.filter(restaurant_id=restaurant_id)
        item_ids = list(mi_qs.values_list("id", flat=True))

    name_qs = MenuItem.objects.filter(id__in=item_ids)
    if restaurant_id is not None:
        name_qs = name_qs.filter(restaurant_id=restaurant_id)
    name_map = {m.id: m.name for m in name_qs}

    results = []
    for mid in item_ids:
        series = dict(qty_map.get(mid, {}))
        preds = []

        for d in future_days:
            row = _feature_row(d, series)
            X = pd.DataFrame([[row[f] for f in FEATURES]], columns=FEATURES)
            yhat = float(model.predict(X)[0])
            yhat_int = max(0, int(round(yhat)))
            series[d] = yhat_int
            preds.append({"date": str(d), "yhat": yhat_int})

        results.append(
            {
                "menu_item_id": int(mid),
                "menu_item_name": name_map.get(mid, f"Item {mid}"),
                "tomorrow": preds[0]["yhat"] if preds else 0,
                "next_7_days_total": int(sum(p["yhat"] for p in preds)),
                "daily": preds,
            }
        )

    results.sort(key=lambda x: x["next_7_days_total"], reverse=True)
    return {
        "start_date": str(tomorrow),
        "horizon_days": horizon_days,
        "items": results[:top_n],
    }
