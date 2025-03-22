# detection/urls.py
from django.urls import path
from .views import StartDetectionView, StopDetectionView, StatusView

urlpatterns = [
    path('start_detection/', StartDetectionView.as_view(), name='start_detection'),
    path('stop_detection/', StopDetectionView.as_view(), name='stop_detection'),
    path('status/', StatusView.as_view(), name='status'),
]
