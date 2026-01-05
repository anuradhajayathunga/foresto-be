from django.urls import path
from .views import DemandForecastView, ForecastHistoryView, IngredientPlanView

urlpatterns = [
    path("demand/", DemandForecastView.as_view()),
    path("history/", ForecastHistoryView.as_view()),
    path("ingredients_plan/", IngredientPlanView.as_view()),

]
