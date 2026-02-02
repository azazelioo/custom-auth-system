from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели пользователя"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Создание обычного пользователя"""
        if not email:
            raise ValueError('Email обязателен для создания пользователя')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Кастомная модель пользователя"""
    
    email = models.EmailField(
        'Email адрес',
        max_length=255,
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'Пользователь с таким email уже существует.',
        }
    )
    first_name = models.CharField('Имя', max_length=150, blank=True)
    middle_name = models.CharField('Отчество', max_length=150, blank=True)
    last_name = models.CharField('Фамилия', max_length=150, blank=True)
    
    is_active = models.BooleanField(
        'Активен',
        default=True,
        help_text='Отметьте, если пользователь должен считаться активным. '
                  'Уберите эту отметку вместо удаления учетной записи.'
    )
    is_staff = models.BooleanField(
        'Статус персонала',
        default=False,
        help_text='Отметьте, если пользователь может входить в админ-панель.'
    )
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Возвращает полное имя пользователя"""
        full_name = ' '.join(filter(None, [
            self.last_name,
            self.first_name,
            self.middle_name
        ]))
        return full_name or self.email
    
    def get_short_name(self):
        """Возвращает короткое имя"""
        return self.first_name or self.email
    
    def soft_delete(self):
        """Мягкое удаление пользователя"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
