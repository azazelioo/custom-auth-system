from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, ProjectViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]
