from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Role, Permission, UserRole, RolePermission, UserPermission
from .serializers import (
    RoleSerializer,
    PermissionSerializer,
    UserRoleSerializer,
    AssignRoleSerializer,
    GrantPermissionSerializer,
    UserPermissionSerializer
)
from .permissions import IsAdminUser, IsAuthenticated
from accounts.models import User


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления ролями (только для администраторов)
    """
    queryset =Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @extend_schema(
        description='Добавить разрешение к роли'
    )
    @action(detail=True, methods=['post'], url_path='add-permission')
    def add_permission(self, request, pk=None):
        """Добавление разрешения к роли"""
        role = self.get_object()
        permission_id = request.data.get('permission_id')
        
        if not permission_id:
            return Response({
                'error': 'Требуется permission_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            permission = Permission.objects.get(id=permission_id)
        except Permission.DoesNotExist:
            return Response({
                'error': 'Разрешение не найдено'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем, не добавлено ли уже
        if RolePermission.objects.filter(role=role, permission=permission).exists():
            return Response({
                'error': 'Разрешение уже добавлено к этой роли'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        RolePermission.objects.create(
            role=role,
            permission=permission,
            granted_by=request.user
        )
        
        return Response({
            'message': f'Разрешение {permission.code} добавлено к роли {role.name}'
        }, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        description='Удалить разрешение из роли'
    )
    @action(detail=True, methods=['post'], url_path='remove-permission')
    def remove_permission(self, request, pk=None):
        """Удаление разрешения из роли"""
        role = self.get_object()
        permission_id = request.data.get('permission_id')
        
        if not permission_id:
            return Response({
                'error': 'Требуется permission_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role_perm = RolePermission.objects.get(role=role, permission_id=permission_id)
            role_perm.delete()
            
            return Response({
                'message': 'Разрешение удалено из роли'
            }, status=status.HTTP_200_OK)
        except RolePermission.DoesNotExist:
            return Response({
                'error': 'Разрешение не найдено в этой роли'
            }, status=status.HTTP_404_NOT_FOUND)


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления разрешениями (только для администраторов)
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


@extend_schema(
    request=AssignRoleSerializer,
    description='Назначить роль пользователю'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def assign_role_to_user(request, user_id):
    """Назначение роли пользователю"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = AssignRoleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    role_id = serializer.validated_data['role_id']
    
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response({
            'error': 'Роль не найдена'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Проверяем, не назначена ли уже
    if UserRole.objects.filter(user=user, role=role).exists():
        return Response({
            'error': 'Роль уже назначена этому пользователю'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    UserRole.objects.create(
        user=user,
        role=role,
        assigned_by=request.user
    )
    
    return Response({
        'message': f'Роль {role.name} назначена пользователю {user.email}'
    }, status=status.HTTP_201_CREATED)


@extend_schema(
    request=AssignRoleSerializer,
    description='Отозвать роль у пользователя'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def revoke_role_from_user(request, user_id):
    """Отзыв роли у пользователя"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = AssignRoleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    role_id = serializer.validated_data['role_id']
    
    try:
        user_role = UserRole.objects.get(user=user, role_id=role_id)
        user_role.delete()
        
        return Response({
            'message': 'Роль отозвана у пользователя'
        }, status=status.HTTP_200_OK)
    except UserRole.DoesNotExist:
        return Response({
            'error': 'У пользователя нет этой роли'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    request=GrantPermissionSerializer,
    description='Выдать прямое разрешение пользователю'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def grant_permission_to_user(request, user_id):
    """Выдача прямого разрешения пользователю"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = GrantPermissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    permission_id = serializer.validated_data['permission_id']
    is_granted = serializer.validated_data.get('is_granted', True)
    
    try:
        permission = Permission.objects.get(id=permission_id)
    except Permission.DoesNotExist:
        return Response({
            'error': 'Разрешение не найдено'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Обновляем или создаём
    user_perm, created = UserPermission.objects.update_or_create(
        user=user,
        permission=permission,
        defaults={
            'is_granted': is_granted,
            'granted_by': request.user
        }
    )
    
    action_text = 'выдано' if is_granted else 'запрещено'
    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    
    return Response({
        'message': f'Разрешение {permission.code} {action_text} для пользователя {user.email}'
    }, status=status_code)


@extend_schema(
    description='Отозвать прямое разрешение у пользователя'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def revoke_permission_from_user(request, user_id):
    """Отзыв прямого разрешения у пользователя"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    permission_id = request.data.get('permission_id')
    
    if not permission_id:
        return Response({
            'error': 'Требуется permission_id'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_perm = UserPermission.objects.get(user=user, permission_id=permission_id)
        user_perm.delete()
        
        return Response({
            'message': 'Разрешение отозвано у пользователя'
        }, status=status.HTTP_200_OK)
    except UserPermission.DoesNotExist:
        return Response({
            'error': 'У пользователя нет этого разрешения'
        }, status=status.HTTP_404_NOT_FOUND)
