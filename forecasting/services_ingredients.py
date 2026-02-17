from collections import defaultdict
from decimal import Decimal

from inventory.models import InventoryItem
from menu.models import MenuItem, RecipeLine
from .services import predict_menu_demand


def D(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def build_ingredient_plan(
    horizon_days: int = 7,
    top_n_items: int = 50,
    scope: str = "next7",
    restaurant_id=None,
):
    """
    scope:
      - tomorrow: use each item's predicted 'tomorrow'
      - next7: use each item's predicted 'next_7_days_total'
    """
    forecast = predict_menu_demand(
        horizon_days=horizon_days,
        top_n=top_n_items,
        restaurant_id=restaurant_id,
    )
    items = forecast.get("items", [])

    demand_by_item = {}
    for it in items:
        mid = int(it["menu_item_id"])
        demand_by_item[mid] = int(it.get("tomorrow", 0)) if scope == "tomorrow" else int(it.get("next_7_days_total", 0))

    item_ids = list(demand_by_item.keys())
    if not item_ids:
        return {
            "scope": scope,
            "horizon_days": horizon_days,
            "start_date": forecast.get("start_date"),
            "items_used": [],
            "items_missing_recipes": [],
            "ingredients": [],
        }

    recipe_qs = RecipeLine.objects.filter(menu_item_id__in=item_ids).select_related("menu_item", "ingredient")
    if restaurant_id is not None:
        recipe_qs = recipe_qs.filter(
            menu_item__restaurant_id=restaurant_id,
            ingredient__restaurant_id=restaurant_id,
        )

    has_recipe = set()
    required_by_ing = defaultdict(Decimal)
    contributes = defaultdict(list)

    for rl in recipe_qs:
        has_recipe.add(rl.menu_item_id)
        units = demand_by_item.get(rl.menu_item_id, 0)
        if units <= 0:
            continue

        req = (D(units) * D(rl.qty)).quantize(Decimal("0.01"))
        required_by_ing[rl.ingredient_id] += req

        contributes[rl.ingredient_id].append(
            {
                "menu_item_id": rl.menu_item_id,
                "menu_item_name": rl.menu_item.name,
                "predicted_units": int(units),
                "per_unit_qty": str(rl.qty),
                "required_qty": str(req),
            }
        )

    menu_name_qs = MenuItem.objects.filter(id__in=item_ids).only("id", "name")
    if restaurant_id is not None:
        menu_name_qs = menu_name_qs.filter(restaurant_id=restaurant_id)
    menu_name_map = {m.id: m.name for m in menu_name_qs}

    items_missing = [
        {"menu_item_id": mid, "menu_item_name": menu_name_map.get(mid, f"Item {mid}")}
        for mid in item_ids
        if mid not in has_recipe and demand_by_item.get(mid, 0) > 0
    ]

    ing_ids = list(required_by_ing.keys())
    inv_qs = InventoryItem.objects.filter(id__in=ing_ids)
    if restaurant_id is not None:
        inv_qs = inv_qs.filter(restaurant_id=restaurant_id)
    inv = {i.id: i for i in inv_qs}

    ingredients_out = []
    for ing_id, required in required_by_ing.items():
        item = inv.get(ing_id)
        if not item:
            continue

        current = D(item.current_stock)
        reorder = D(item.reorder_level)
        projected_remaining = (current - required).quantize(Decimal("0.01"))

        ok = projected_remaining >= reorder
        suggested_purchase = required + reorder - current
        if suggested_purchase < 0:
            suggested_purchase = Decimal("0.00")
        suggested_purchase = suggested_purchase.quantize(Decimal("0.01"))

        status = "OK" if ok else ("OUT" if projected_remaining <= 0 else "LOW")

        ingredients_out.append(
            {
                "ingredient_id": item.id,
                "ingredient_name": item.name,
                "sku": item.sku,
                "unit": item.unit,
                "current_stock": str(current),
                "reorder_level": str(reorder),
                "required_qty": str(required.quantize(Decimal("0.01"))),
                "projected_remaining": str(projected_remaining),
                "status": status,
                "suggested_purchase_qty": str(suggested_purchase),
                "contributes": contributes.get(item.id, []),
            }
        )

    def sort_key(x):
        rank = {"OUT": 0, "LOW": 1, "OK": 2}.get(x["status"], 3)
        return (rank, -float(x["suggested_purchase_qty"]))

    ingredients_out.sort(key=sort_key)

    return {
        "scope": scope,
        "horizon_days": horizon_days,
        "start_date": forecast.get("start_date"),
        "items_used": items,
        "items_missing_recipes": items_missing,
        "ingredients": ingredients_out,
    }
