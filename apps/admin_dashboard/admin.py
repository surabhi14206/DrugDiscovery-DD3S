from django.contrib import admin
from .models import (
    UserActivity, SearchHistory, PredictionRequest, SupportTicket,
    UserPreferences, Notification, WeeklyReport
)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'subject', 'status', 'priority', 'created_at', 'admin_responder']
    list_filter = ['status', 'priority', 'subject', 'created_at']
    search_fields = ['name', 'email', 'message', 'admin_response']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Contact Information', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Ticket Details', {
            'fields': ('subject', 'message', 'status', 'priority')
        }),
        ('Admin Response', {
            'fields': ('admin_response', 'admin_responder')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'target_molecule', 'timestamp', 'ip_address']
    list_filter = ['action_type', 'timestamp']
    search_fields = ['user__username', 'search_query']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'search_type', 'results_count', 'timestamp']
    list_filter = ['search_type', 'timestamp']
    search_fields = ['user__username', 'query']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(PredictionRequest)
class PredictionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'molecule', 'prediction_type', 'processing_time', 'timestamp']
    list_filter = ['prediction_type', 'timestamp']
    search_fields = ['user__username', 'molecule__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'email_notifications', 'activity_notifications', 'weekly_reports', 'updated_at']
    list_filter = ['theme', 'email_notifications', 'activity_notifications', 'weekly_reports']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"
    
    actions = ['mark_as_read']


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'week_start', 'week_end', 'sent_at', 'total_activities']
    list_filter = ['week_start', 'sent_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['sent_at']
    date_hierarchy = 'sent_at'

