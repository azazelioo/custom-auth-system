from rest_framework import serializers
from .models import Role, Permission, UserRole, RolePermission, UserPermission, ResourcePermission


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer для разрешений"""
    
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'resource_type', 'action', 'created_at']
        read_only_fields = ['id', 'created_at']


class RoleSerializer(serializers.ModelSerializer):
    """Serializer для ролей"""
    
    permissions = PermissionSerializer(many=True, read_only=True, source='role_permissions.permission')
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer для связи пользователь-роль"""
    
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'user_email', 'role_name', 'assigned_at', 'assigned_by']
        read_only_fields = ['id', 'assigned_at', 'assigned_by']


class AssignRoleSerializer(serializers.Serializer):
    """Serializer для назначения роли пользователю"""
    
    role_id = serializers.IntegerField(required=True)


class GrantPermissionSerializer(serializers.Serializer):
    """Serializer для выдачи разрешения пользователю"""
    
    permission_id = serializers.IntegerField(required=True)
    is_granted = serializers.BooleanField(default=True)


class UserPermissionSerializer(serializers.ModelSerializer):
    """Serializer для прямых разрешений пользователя"""
    
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'permission', 'permission_code', 'permission_name', 
                  'is_granted', 'granted_at', 'granted_by']
        read_only_fields = ['id', 'granted_at', 'granted_by']
