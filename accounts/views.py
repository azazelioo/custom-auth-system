from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer
)


@extend_schema(
    request=UserRegistrationSerializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description='Ошибка валидации')
    },
    description='Регистрация нового пользователя в системе'
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Регистрация нового пользователя
    
    Требуемые поля:
    - email
    - password
    - password_confirm
    - first_name (опционально)
    - middle_name (опционально)
    - last_name (опционально)
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'Пользователь успешно зарегистрирован',
            'user': user_data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(description='Успешный вход, возвращает JWT токены'),
        401: OpenApiResponse(description='Неверные учетные данные')
    },
    description='Вход в систему, получение JWT токенов'
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Вход в систему
    
    Требуемые поля:
    - email
    - password
    
    Возвращает:
    - access: JWT access token (срок действия 15 минут)
    - refresh: JWT refresh token (срок действия 7 дней)
    - user: информация о пользователе
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Проверяем существование пользователя
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({
            'error': 'Неверный email или пароль'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Проверяем, активен ли пользователь
    if not user.is_active:
        return Response({
            'error': 'Учетная запись деактивирована'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Проверяем пароль
    if not user.check_password(password):
        return Response({
            'error': 'Неверный email или пароль'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Генерируем JWT токены
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(description='Успешный выход'),
        400: OpenApiResponse(description='Ошибка')
    },
    description='Выход из системы (добавление refresh токена в blacklist)'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Выход из системы
    
    Требуется передать refresh token в теле запроса:
    {
        "refresh": "your_refresh_token"
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Требуется refresh token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response({
            'message': 'Выход выполнен успешно'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={
        200: UserSerializer,
        401: OpenApiResponse(description='Не аутентифицирован')
    },
    description='Получение информации о текущем пользователе'
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Получение профиля текущего пользователя
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    request=UserProfileUpdateSerializer,
    responses={
        200: UserSerializer,
        400: OpenApiResponse(description='Ошибка валидации')
    },
    description='Обновление профиля текущего пользователя'
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """
    Обновление профиля текущего пользователя
    
    Можно обновить:
    - first_name
    - middle_name
    - last_name
    """
    serializer = UserProfileUpdateSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(UserSerializer(request.user).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(description='Аккаунт удален'),
        401: OpenApiResponse(description='Не аутентифицирован')
    },
    description='Мягкое удаление аккаунта (is_active=False)'
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account_view(request):
    """
    Мягкое удаление аккаунта
    
    Устанавливает is_active=False, пользователь не сможет войти в систему,
    но данные остаются в базе для аудита
    """
    user = request.user
    user.soft_delete()
    
    return Response({
        'message': 'Аккаунт успешно удален'
    }, status=status.HTTP_200_OK)


@extend_schema(
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description='Пароль изменен'),
        400: OpenApiResponse(description='Ошибка валидации')
    },
    description='Изменение пароля пользователя'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Изменение пароля
    
    Требуемые поля:
    - old_password
    - new_password
    - new_password_confirm
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        return Response({
            'message': 'Пароль успешно изменен'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
