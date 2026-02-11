from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt import EmailTokenObtainPairView
from .views import (
    MeView,
    MyRestaurantsView,
    RegisterView,
    RestaurantMemberDetailView,
    RestaurantMembersView,
    RestaurantStaffRegisterView,
    RestaurantMemberRoleUpdateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("token/", EmailTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("me/", MeView.as_view()),
    path("my-restaurants/", MyRestaurantsView.as_view()),
    path(
        "restaurants/<int:restaurant_id>/members/",
        RestaurantMembersView.as_view(),
    ),
    path(
        "restaurants/<int:restaurant_id>/members/<int:membership_id>/",
        RestaurantMemberDetailView.as_view(),
    ),
     path(
        "restaurants/<int:restaurant_id>/staff-register/",
        RestaurantStaffRegisterView.as_view(),
        name="restaurant-staff-register",
    ),
    path(
        "restaurants/<int:restaurant_id>/members/<int:membership_id>/role/",
        RestaurantMemberRoleUpdateView.as_view(),
        name="restaurant-member-role-update",
    ),
]
