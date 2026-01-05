# forecasting/urls.py
from django.urls import path
from .views import DemandForecastView

urlpatterns = [
    path("demand/", DemandForecastView.as_view()),
]
