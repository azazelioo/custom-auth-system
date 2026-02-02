from django.urls import path
from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    update_profile_view,
    delete_account_view,
    change_password_view
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', update_profile_view, name='profile-update'),
    path('profile/delete/', delete_account_view, name='profile-delete'),
    path('profile/change-password/', change_password_view, name='change-password'),
]
