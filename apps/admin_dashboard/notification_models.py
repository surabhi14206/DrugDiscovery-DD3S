from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """Store notifications for users to display as popups"""
    
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('update', 'Update'),
        ('policy', 'Policy Change'),
        ('feature', 'New Feature'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ActivityLog(models.Model):
    """Enhanced activity log for tracking user actions"""
    
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('molecule_view', 'Molecule Viewed'),
        ('molecule_search', 'Molecule Search'),
        ('prediction', 'Prediction Made'),
        ('profile_update', 'Profile Updated'),
        ('password_change', 'Password Changed'),
        ('2fa_enabled', 'Two-Factor Authentication Enabled'),
        ('2fa_disabled', 'Two-Factor Authentication Disabled'),
        ('email_verified', 'Email Verified'),
        ('data_export', 'Data Exported'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional non-sensitive data
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()}"


class WeeklyReport(models.Model):
    """Track weekly reports sent to users"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_reports'
    )
    week_start = models.DateField()
    week_end = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)
    total_activities = models.IntegerField(default=0)
    molecules_viewed = models.IntegerField(default=0)
    predictions_made = models.IntegerField(default=0)
    searches_performed = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'weekly_reports'
        ordering = ['-sent_at']
        unique_together = [['user', 'week_start']]
    
    def __str__(self):
        return f"Weekly Report for {self.user.username} - {self.week_start}"
