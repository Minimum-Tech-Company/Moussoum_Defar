from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LanguageViewSet, CountryViewSet, WorkerViewSet,
    DataCollectionViewSet, DataSubmissionViewSet,
    AnnotationTaskViewSet, RLHFTaskViewSet, SyntheticDataJobViewSet,
    NotificationViewSet, PublicWorkerView
)

router = DefaultRouter()
router.register(r'languages', LanguageViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'profile', WorkerViewSet, basename='worker')
router.register(r'collections', DataCollectionViewSet)
router.register(r'submissions', DataSubmissionViewSet, basename='submission')
router.register(r'annotations', AnnotationTaskViewSet, basename='annotation')
router.register(r'rlhf', RLHFTaskViewSet, basename='rlhf')
router.register(r'synthetic', SyntheticDataJobViewSet, basename='synthetic')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('public/<int:pk>/', PublicWorkerView.as_view(), name='public-worker'),
    path('', include(router.urls)),
]
