from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, MenuItemViewSet, RecipeLineViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("items", MenuItemViewSet, basename="items")
router.register("recipe-lines", RecipeLineViewSet, basename="recipe-lines")


urlpatterns = [
    path("", include(router.urls)),
]
