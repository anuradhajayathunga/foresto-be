from django.urls import path
from .views import predict_price, prediction_result_with_suppliers, supplier_price_entry, menu_calculator

urlpatterns = [
    path('predict/', predict_price),
    path('prediction-result/', prediction_result_with_suppliers),
    path('supplier-data/', supplier_price_entry),
    path('menu-calc/', menu_calculator),
]