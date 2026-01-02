from celery import shared_task
from inventory.models import Store
from inventory.services.purchase_order import generate_batch_smart_pos


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 3},
)
def generate_smart_auto_po_task(self, store_id, days=7):
    store = Store.objects.get(id=store_id)
    pos = generate_batch_smart_pos(store=store, days=days)

    return {
        "store_id": store_id,
        "purchase_orders_created": len(pos),
    }
