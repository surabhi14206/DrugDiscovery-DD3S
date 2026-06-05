from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'email_verified', 'two_factor_enabled', 'date_joined']
    list_filter = ['role', 'email_verified', 'two_factor_enabled', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'email_verified', 'two_factor_enabled')}),
    )

