from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.molecules.models import Molecule


class SupportTicket(models.Model):
    """Support tickets from contact form"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Technical Support'),
        ('feature', 'Feature Request'),
        ('bug', 'Bug Report'),
        ('partnership', 'Partnership Opportunity'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    admin_response = models.TextField(null=True, blank=True)
    admin_responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_tickets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.status})"
    
    class Meta:
        db_table = 'support_tickets'
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email']),
        ]


class UserActivity(models.Model):
    """Log all user actions"""
    
    ACTION_CHOICES = [
        ('search', 'Search'),
        ('view_molecule', 'View Molecule'),
        ('predict', 'Prediction'),
        ('download', 'Download'),
        ('page_view', 'Page View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    page_url = models.TextField(null=True, blank=True)
    target_molecule = models.ForeignKey(
        Molecule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    search_query = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.user.username} - {self.action_type} at {self.timestamp}"
    
    class Meta:
        db_table = 'user_activities'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
        ]


class SearchHistory(models.Model):
    """Track search patterns"""
    
    SEARCH_TYPE_CHOICES = [
        ('text', 'Text Search'),
        ('advanced', 'Advanced Search'),
        ('structure', 'Structure Search'),
        ('sequence', 'Sequence Search'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='searches'
    )
    query = models.TextField()
    search_type = models.CharField(max_length=50, choices=SEARCH_TYPE_CHOICES)
    results_count = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} searched: {self.query[:50]}"
    
    class Meta:
        db_table = 'search_history'
        verbose_name = 'Search History'
        verbose_name_plural = 'Search Histories'
        ordering = ['-timestamp']


class PredictionRequest(models.Model):
    """Track ML predictions"""
    
    PREDICTION_TYPE_CHOICES = [
        ('toxicity', 'Toxicity'),
        ('solubility', 'Solubility'),
        ('activity', 'Activity'),
        ('bioavailability', 'Bioavailability'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    molecule = models.ForeignKey(
        Molecule,
        on_delete=models.CASCADE,
        related_name='prediction_requests'
    )
    prediction_type = models.CharField(max_length=50, choices=PREDICTION_TYPE_CHOICES)
    result = models.JSONField()
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.prediction_type} for {self.molecule.name}"
    
    class Meta:
        db_table = 'prediction_requests'
        verbose_name = 'Prediction Request'
        verbose_name_plural = 'Prediction Requests'
        ordering = ['-timestamp']


class UserPreferences(models.Model):
    """Store user preferences and settings"""
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('recomended', 'Recomended'),
        ('dark', 'Dark'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    theme = models.CharField(
        max_length=15,
        choices=THEME_CHOICES,
        default='light'
    )
    email_notifications = models.BooleanField(default=True)
    activity_notifications = models.BooleanField(default=True)
    weekly_reports = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    class Meta:
        db_table = 'user_preferences'
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'


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

