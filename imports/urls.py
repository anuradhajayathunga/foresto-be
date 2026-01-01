from django.urls import path
from .views import ImportCSVView, DownloadCSVTemplateView

urlpatterns = [
    path("csv/", ImportCSVView.as_view(), name="import-csv"),
    path('template/', DownloadCSVTemplateView.as_view(), name='import_template'),
]
