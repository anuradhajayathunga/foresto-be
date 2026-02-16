from datetime import timedelta

import pandas as pd
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from menu.models import MenuItem
from sales.models import Sale, SaleItem
from .ml import get_model

FEATURES = ["day_of_week", "month", "is_weekend", "lag_1", "lag_7", "rolling_mean_7"]


def _daily_qty_map(days_back: int = 180, restaurant_id=None):
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


def _row(day, series):
    dow = day.weekday()
    return {
        "day_of_week": dow,
        "month": day.month,
        "is_weekend": 1 if dow >= 5 else 0,
        "lag_1": float(series.get(day - timedelta(days=1), 0)),
        "lag_7": float(series.get(day - timedelta(days=7), 0)),
        "rolling_mean_7": _rolling_mean_7(series, day),
    }


def predict_past_days(days: int = 14, days_back: int = 180, top_n: int = 50, restaurant_id=None):
    days = max(1, min(days, 90))
    model = get_model()

    start, today, qty_map = _daily_qty_map(days_back=days_back, restaurant_id=restaurant_id)
    end_day = today - timedelta(days=1)
    start_day = end_day - timedelta(days=days - 1)

    target_days = [start_day + timedelta(days=i) for i in range(days)]
    item_ids = list(qty_map.keys())

    name_qs = MenuItem.objects.filter(id__in=item_ids)
    if restaurant_id is not None:
        name_qs = name_qs.filter(restaurant_id=restaurant_id)
    name_map = {m.id: m.name for m in name_qs}

    results = []
    for mid in item_ids:
        series = dict(qty_map.get(mid, {}))
        daily = []

        for d in target_days:
            X = pd.DataFrame([[_row(d, series)[f] for f in FEATURES]], columns=FEATURES)
            yhat = float(model.predict(X)[0])
            yhat_int = max(0, int(round(yhat)))
            daily.append({"date": str(d), "yhat": yhat_int, "actual": int(series.get(d, 0))})

        y_key = str(end_day)
        y_row = next((x for x in daily if x["date"] == y_key), None)

        results.append(
            {
                "menu_item_id": int(mid),
                "menu_item_name": name_map.get(mid, f"Item {mid}"),
                "yesterday_actual": y_row["actual"] if y_row else 0,
                "yesterday_pred": y_row["yhat"] if y_row else 0,
                "yesterday_diff": (y_row["actual"] - y_row["yhat"]) if y_row else 0,
                "daily": daily,
            }
        )

    results.sort(key=lambda x: x["yesterday_actual"], reverse=True)
    return {
        "start_date": str(start_day),
        "end_date": str(end_day),
        "days": days,
        "items": results[:top_n],
    }
