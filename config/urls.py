from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from accounts.views import RegisterView, MeView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth endpoints
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/me/', MeView.as_view(), name='me'),

    # Inventory
    path("api/inventory/", include("inventory.urls")),

path('api/auth/', include('accounts.urls')),
]
