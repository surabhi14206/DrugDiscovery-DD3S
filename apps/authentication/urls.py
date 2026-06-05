from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.auth_view, name='auth'),  # Combined login/register
    path('register/', views.register, name='register'),  # Legacy redirect
    path('login/', views.login_view, name='login'),  # Legacy redirect
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('upload-photo/', views.upload_profile_photo, name='upload_photo'),
    path('terms/', views.terms_and_conditions, name='terms'),
    
    # Email Verification
    path('send-verification/', views.send_verification_email, name='send_verification'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    
    # Two-Factor Authentication
    path('2fa/setup/', views.setup_2fa, name='setup_2fa'),
    path('2fa/verify-setup/', views.verify_2fa_setup, name='verify_2fa_setup'),
    path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
]


