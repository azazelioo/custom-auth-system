"""
Тут живет основная логика проверки прав. 
Сделал отдельным сервисом, чтобы не раздувать модели и не дублировать код в разных вьюхах.
Порядок проверки важен (от частного к общему).
"""
import logging
from .models import UserPermission, ResourcePermission, RolePermission, UserRole

logger = logging.getLogger(__name__)

class PermissionService:
    """Сервис для проверки прав доступа"""
    
    # В будущем можно прикрутить Redis, чтобы не ходить в базу так часто
    CACHE_TIMEOUT = 300 
    
    @staticmethod
    def check_permission(user, resource_type, action, resource_id=None):
        """
        Главная функция проверки прав доступа
        
        Args:
            user: объект пользователя
            resource_type: тип ресурса (например: 'document', 'project')
            action: действие (например: 'create', 'read', 'update', 'delete')
            resource_id: ID конкретного ресурса (опционально)
        
        Returns:
            bool: True если доступ разрешен, False если запрещен
        """
        # 1. Суперпользователь всегда имеет доступ
        if user.is_superuser:
            return True
        
        # 2. Неактивный пользователь не имеет доступа
        if not user.is_active:
            return False
        
        # Сначала проверяем конкретный ресурс (самый высокий приоритет)
        if resource_id:
            resource_perm = PermissionService._check_resource_permission(
                user, permission_code, resource_type, resource_id
            )
            if resource_perm is not None:
                return resource_perm
        
        # Потом смотрим личные права пользователя
        user_perm = PermissionService._check_user_permission(user, permission_code)
        if user_perm is not None:
            return user_perm
        
        # И в конце проверяем по ролям
        has_role_perm = PermissionService._check_role_permission(user, permission_code)
        
        if not has_role_perm:
            logger.warning(f"Доступ запрещен для {user.email}: {permission_code}")
            
        return has_role_perm
    
    @staticmethod
    def _check_resource_permission(user, permission_code, resource_type, resource_id):
        """
        Проверка разрешения на уровне конкретного ресурса
        
        Returns:
            True - разрешено
            False - запрещено
            None - не указано (продолжить проверку)
        """
        try:
            resource_perm = ResourcePermission.objects.select_related('permission').get(
                user=user,
                resource_type=resource_type,
                resource_id=str(resource_id),
                permission__code=permission_code
            )
            return resource_perm.is_granted
        except ResourcePermission.DoesNotExist:
            return None
    
    @staticmethod
    def _check_user_permission(user, permission_code):
        """
        Проверка прямого разрешения пользователя
        
        Returns:
            True - разрешено
            False - запрещено
            None - не указано (продолжить проверку)
        """
        try:
            user_perm = UserPermission.objects.select_related('permission').get(
                user=user,
                permission__code=permission_code
            )
            return user_perm.is_granted
        except UserPermission.DoesNotExist:
            return None
    
    @staticmethod
    def _check_role_permission(user, permission_code):
        """
        Проверка разрешения через роли пользователя
        
        Returns:
            True - разрешено через роли
            False - не разрешено
        """
        # Получаем все роли пользователя
        user_role_ids = UserRole.objects.filter(user=user).values_list('role_id', flat=True)
        
        if not user_role_ids:
            return False
        
        # Проверяем, есть ли разрешение хотя бы в одной роли
        has_permission = RolePermission.objects.filter(
            role_id__in=user_role_ids,
            permission__code=permission_code
        ).exists()
        
        return has_permission
    
    @staticmethod
    def get_user_permissions(user):
        """
        Получить все разрешения пользователя (через роли + прямые)
        
        Returns:
            list: список кодов разрешений
        """
        if user.is_superuser:
            return ['*.*']  # Все разрешения
        
        if not user.is_active:
            return []
        
        permissions = set()
        
        # Разрешения через роли
        user_role_ids = UserRole.objects.filter(user=user).values_list('role_id', flat=True)
        role_permissions = RolePermission.objects.filter(
            role_id__in=user_role_ids
        ).select_related('permission').values_list('permission__code', flat=True)
        permissions.update(role_permissions)
        
        # Прямые разрешения пользователя (только разрешенные)
        user_permissions = UserPermission.objects.filter(
            user=user,
            is_granted=True
        ).select_related('permission').values_list('permission__code', flat=True)
        permissions.update(user_permissions)
        
        # Убираем запрещенные разрешения
        denied_permissions = UserPermission.objects.filter(
            user=user,
            is_granted=False
        ).select_related('permission').values_list('permission__code', flat=True)
        permissions.difference_update(denied_permissions)
        
        return list(permissions)
    
    @staticmethod
    def get_user_roles(user):
        """
        Получить все роли пользователя
        
        Returns:
            QuerySet: роли пользователя
        """
        return UserRole.objects.filter(user=user).select_related('role')


# Удобные функции для использования в views
def has_permission(user, resource_type, action, resource_id=None):
    """Проверить, есть ли у пользователя разрешение"""
    return PermissionService.check_permission(user, resource_type, action, resource_id)


def require_permission(resource_type, action):
    """
    Декоратор для проверки разрешений
    
    Пример использования:
    @require_permission('document', 'create')
    def create_document(request):
        ...
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            resource_id = kwargs.get('pk') or kwargs.get('id')
            
            if not has_permission(request.user, resource_type, action, resource_id):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    f'У вас нет разрешения {resource_type}.{action}'
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
