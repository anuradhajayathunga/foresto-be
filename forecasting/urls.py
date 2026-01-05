from django.urls import path
from .views import DemandForecastView, ForecastHistoryView

urlpatterns = [
    path("demand/", DemandForecastView.as_view()),
    path("history/", ForecastHistoryView.as_view()),
]
