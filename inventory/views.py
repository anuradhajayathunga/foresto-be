from rest_framework import generics, permissions
from .models import Store
from .serializers import(
    StoreSerializer
)
# Create your views here.
class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    pagination_class = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
