from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.UsersMe.as_view(), name='users-me'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change-password'),
]
