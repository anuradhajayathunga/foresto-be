from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt import EmailTokenObtainPairView
from .views import (
    MeView,
    MyRestaurantsView,
    RegisterView,
    RestaurantMemberDetailView,
    RestaurantMembersView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", EmailTokenObtainPairView.as_view(), name="auth-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("my-restaurants/", MyRestaurantsView.as_view(), name="auth-my-restaurants"),

    path(
        "restaurants/<int:restaurant_id>/members/",
        RestaurantMembersView.as_view(),
        name="restaurant-members",
    ),
    path(
        "restaurants/<int:restaurant_id>/members/<int:membership_id>/",
        RestaurantMemberDetailView.as_view(),
        name="restaurant-member-detail",
    ),
]
