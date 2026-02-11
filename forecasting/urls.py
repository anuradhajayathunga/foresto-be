from django.urls import path
from .views import ForecastView, ForecastHistoryView, ForecastIngredientsView

urlpatterns = [
    path("demand/", ForecastView.as_view()),
    path("history/", ForecastHistoryView.as_view()),
    path("ingredients_plan/", ForecastIngredientsView.as_view()),

]
