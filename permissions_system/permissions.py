"""
Кастомные классы разрешений для Django REST Framework
"""

from rest_framework import permissions
from .services import PermissionService


class IsAuthenticated(permissions.BasePermission):
    """
    Проверка, что пользователь аутентифицирован
    Возвращает 401 если не аутентифицирован
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class HasResourcePermission(permissions.BasePermission):
    """
    Проверка разрешений на основе нашей системы доступа
    
    Использование в ViewSet:
    permission_classes = [HasResourcePermission]
    resource_type = 'document'
    
    Маппинг HTTP методов на действия:
    GET (list) -> read
    GET (retrieve) -> read
    POST -> create
    PUT/PATCH -> update
    DELETE -> delete
    """
    
    # Маппинг HTTP методов на действия
    action_map = {
        'list': 'read',
        'retrieve': 'read',
        'create': 'create',
        'update': 'update',
        'partial_update': 'update',
        'destroy': 'delete',
    }
    
    def has_permission(self, request, view):
        """Проверка разрешений на уровне коллекции"""
        # Сперва проверяем аутентификацию
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Получаем тип ресурса и действие
        resource_type = getattr(view, 'resource_type', None)
        action = getattr(view, 'action', None)
        
        if not resource_type or not action:
            # Если не указаны - разрешаем (для нестандартных вьюх)
            return True
        
        # Маппим действие
        mapped_action = self.action_map.get(action, action)
        
        # Проверяем разрешение
        return PermissionService.check_permission(
            request.user,
            resource_type,
            mapped_action
        )
    
    def has_object_permission(self, request, view, obj):
        """Проверка разрешений на уровне конкретного объекта"""
        # Получаем тип ресурса и действие
        resource_type = getattr(view, 'resource_type', None)
        action = getattr(view, 'action', None)
        
        if not resource_type or not action:
            return True
        
        # Маппим действие
        mapped_action = self.action_map.get(action, action)
        
        # Получаем ID объекта
        resource_id = getattr(obj, 'id', None) or getattr(obj, 'pk', None)
        
        # Проверяем разрешение на конкретный ресурс
        return PermissionService.check_permission(
            request.user,
            resource_type,
            mapped_action,
            resource_id=resource_id
        )


class IsAdminUser(permissions.BasePermission):
    """
    Проверка, что пользователь - администратор
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Проверяем, есть ли у пользователя роль admin или он суперюзер
        return request.user.is_superuser or PermissionService.check_permission(
            request.user,
            'admin',
            'access'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Проверка, что пользователь - владелец объекта или администратор
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет доступ
        if request.user.is_superuser:
            return True
        
        # Владелец имеет доступ
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # По умолчанию - запретить
        return False


class ReadOnly(permissions.BasePermission):
    """
    Разрешить только безопасные методы (GET, HEAD, OPTIONS)
    """
    
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
