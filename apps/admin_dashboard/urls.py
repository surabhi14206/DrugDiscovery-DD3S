from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('search-analytics/', views.search_analytics, name='search_analytics'),
    
    # Settings and preferences
    path('settings/', views.admin_settings, name='settings'),
    path('settings/password/', views.change_password_page, name='change_password_page'),
    path('settings/notifications/', views.notifications_page, name='notifications_page'),
    path('settings/theme/', views.theme_page, name='theme_page'),
    path('settings/export/', views.export_page, name='export_page'),
    path('change-password/', views.change_password, name='change_password'),
    path('update-preferences/', views.update_preferences, name='update_preferences'),
    
    # History and data export
    path('history/', views.search_history, name='history'),
    path('export-data/', views.export_data, name='export_data'),
    
    # Support tickets
    path('support-tickets/', views.support_tickets, name='support_tickets'),
    path('support-tickets/<int:ticket_id>/', views.support_ticket_detail, name='support_ticket_detail'),
    path('support-tickets/<int:ticket_id>/respond/', views.respond_ticket, name='respond_ticket'),
    
    # Notifications API
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
