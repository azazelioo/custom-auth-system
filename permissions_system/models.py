from django.db import models
from django.conf import settings


class Role(models.Model):
    """Роль в системе (например: admin, manager, editor, viewer)"""
    
    name = models.CharField(
        'Название роли',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Уникальное название роли (например: admin, manager)'
    )
    description = models.TextField(
        'Описание роли',
        blank=True,
        help_text='Подробное описание назначения роли'
    )
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Permission(models.Model):
    """Разрешение на выполнение действия над ресурсом"""
    
    code = models.CharField(
        'Код разрешения',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Формат: resource_type.action (например: document.create)'
    )
    name = models.CharField(
        'Название',
        max_length=200,
        help_text='Человекочитаемое название разрешения'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Подробное описание разрешения'
    )
    resource_type = models.CharField(
        'Тип ресурса',
        max_length=50,
        help_text='Тип ресурса (например: document, project, user)'
    )
    action = models.CharField(
        'Действие',
        max_length=50,
        help_text='Действие над ресурсом (create, read, update, delete, execute)'
    )
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Разрешение'
        verbose_name_plural = 'Разрешения'
        ordering = ['resource_type', 'action']
        indexes = [
            models.Index(fields=['resource_type', 'action']),
        ]
    
    def __str__(self):
        return self.code


class UserRole(models.Model):
    """Связь пользователя с ролью"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='Пользователь'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name='Роль'
    )
    
    assigned_at = models.DateTimeField('Дата назначения', auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles',
        verbose_name='Назначил'
    )
    
    class Meta:
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'
        unique_together = ['user', 'role']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f'{self.user.email} - {self.role.name}'


class RolePermission(models.Model):
    """Связь роли с разрешением"""
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Роль'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name='Разрешение'
    )
    
    granted_at = models.DateTimeField('Дата выдачи', auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_role_permissions',
        verbose_name='Выдал'
    )
    
    class Meta:
        verbose_name = 'Разрешение роли'
        verbose_name_plural = 'Разрешения ролей'
        unique_together = ['role', 'permission']
        ordering = ['-granted_at']
    
    def __str__(self):
        return f'{self.role.name} - {self.permission.code}'


class UserPermission(models.Model):
    """Прямое разрешение или запрет для пользователя"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_user_permissions',
        verbose_name='Пользователь'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name='Разрешение'
    )
    is_granted = models.BooleanField(
        'Разрешено',
        default=True,
        help_text='True - разрешить, False - запретить'
    )
    
    granted_at = models.DateTimeField('Дата выдачи/запрета', auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_user_permissions',
        verbose_name='Выдал/Запретил'
    )
    
    class Meta:
        verbose_name = 'Разрешение пользователя'
        verbose_name_plural = 'Разрешения пользователей'
        unique_together = ['user', 'permission']
        ordering = ['-granted_at']
    
    def __str__(self):
        status = 'Разрешено' if self.is_granted else 'Запрещено'
        return f'{self.user.email} - {self.permission.code} ({status})'


class ResourcePermission(models.Model):
    """Разрешение на уровне конкретного ресурса"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resource_permissions',
        verbose_name='Пользователь'
    )
    resource_type = models.CharField(
        'Тип ресурса',
        max_length=50,
        help_text='Тип ресурса (document, project, task)'
    )
    resource_id = models.CharField(
        'ID ресурса',
        max_length=100,
        help_text='Идентификатор конкретного ресурса'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='resource_assignments',
        verbose_name='Разрешение'
    )
    is_granted = models.BooleanField(
        'Разрешено',
        default=True,
        help_text='True - разрешить, False - запретить'
    )
    
    granted_at = models.DateTimeField('Дата выдачи/запрета', auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_resource_permissions',
        verbose_name='Выдал/Запретил'
    )
    
    class Meta:
        verbose_name = 'Разрешение на ресурс'
        verbose_name_plural = 'Разрешения на ресурсы'
        unique_together = ['user', 'resource_type', 'resource_id', 'permission']
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        status = 'Разрешено' if self.is_granted else 'Запрещено'
        return f'{self.user.email} - {self.resource_type}#{self.resource_id} - {self.permission.code} ({status})'
