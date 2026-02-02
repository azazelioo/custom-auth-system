from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleViewSet,
    PermissionViewSet,
    assign_role_to_user,
    revoke_role_from_user,
    grant_permission_to_user,
    revoke_permission_from_user
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
    
    # Назначение ролей пользователям
    path('users/<int:user_id>/assign-role/', assign_role_to_user, name='assign-role'),
    path('users/<int:user_id>/revoke-role/', revoke_role_from_user, name='revoke-role'),
    
    # Прямые разрешения пользователям
    path('users/<int:user_id>/grant-permission/', grant_permission_to_user, name='grant-permission'),
    path('users/<int:user_id>/revoke-permission/', revoke_permission_from_user, name='revoke-permission'),
]
