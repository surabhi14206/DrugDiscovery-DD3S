"""
Notification Service
Handles creating and sending notifications to users
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.admin_dashboard.models import Notification, UserPreferences

User = get_user_model()


class NotificationService:
    """Service to create and send notifications"""
    
    @staticmethod
    def create_notification(user, notification_type, title, message):
        """Create a notification for a user"""
        return Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message
        )
    
    @staticmethod
    def send_email_notification(user, subject, message, notification_type='info'):
        """Send an email notification if user has email notifications enabled"""
        try:
            preferences = UserPreferences.objects.get(user=user)
            if not preferences.email_notifications:
                return False, "User has disabled email notifications"
        except UserPreferences.DoesNotExist:
            # If no preferences, assume they want notifications
            pass
        
        # Prepare email context
        context = {
            'user': user,
            'subject': subject,
            'message': message,
            'notification_type': notification_type,
            'support_email': 'dd3s.sup@gmail.com',
        }
        
        # Render email template
        html_message = render_to_string('admin_dashboard/emails/notification_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True, "Email notification sent successfully"
        except Exception as e:
            return False, f"Error sending email: {str(e)}"
    
    @staticmethod
    def notify_login(user, ip_address, user_agent):
        """Notify user of new login activity"""
        # Create notification for popup (if activity notifications enabled)
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='info',
                    title='New Login Detected',
                    message=f'Your account was accessed from IP: {ip_address[:15]}...'
                )
        except UserPreferences.DoesNotExist:
            pass
        
        # Send email notification
        subject = 'New Login to Your Account'
        message = f'Hi {user.username},\n\nWe detected a new login to your account.\n\nIP Address: {ip_address}\n\nIf this wasn\'t you, please secure your account immediately.'
        NotificationService.send_email_notification(user, subject, message, 'info')
    
    @staticmethod
    def notify_password_changed(user):
        """Notify user that their password was changed"""
        # Create popup notification
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='success',
                    title='Password Changed',
                    message='Your password has been successfully updated.'
                )
        except UserPreferences.DoesNotExist:
            pass
        
        # Send email notification
        subject = 'Password Changed Successfully'
        message = f'Hi {user.username},\n\nYour password has been successfully changed.\n\nIf you didn\'t make this change, please contact support immediately at dd3s.sup@gmail.com.'
        NotificationService.send_email_notification(user, subject, message, 'success')
    
    @staticmethod
    def notify_2fa_enabled(user):
        """Notify user that 2FA was enabled"""
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='success',
                    title='Two-Factor Authentication Enabled',
                    message='Your account security has been enhanced with 2FA.'
                )
        except UserPreferences.DoesNotExist:
            pass
        
        subject = '2FA Enabled on Your Account'
        message = f'Hi {user.username},\n\nTwo-factor authentication has been successfully enabled on your account.\n\nYour account is now more secure!'
        NotificationService.send_email_notification(user, subject, message, 'success')
    
    @staticmethod
    def notify_2fa_disabled(user):
        """Notify user that 2FA was disabled"""
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='warning',
                    title='Two-Factor Authentication Disabled',
                    message='2FA has been disabled on your account.'
                )
        except UserPreferences.DoesNotExist:
            pass
        
        subject = '2FA Disabled on Your Account'
        message = f'Hi {user.username},\n\nTwo-factor authentication has been disabled on your account.\n\nIf you didn\'t make this change, please contact support immediately.'
        NotificationService.send_email_notification(user, subject, message, 'warning')
    
    @staticmethod
    def notify_email_verified(user):
        """Notify user that their email was verified"""
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='success',
                    title='Email Verified',
                    message='Your email address has been successfully verified!'
                )
        except UserPreferences.DoesNotExist:
            pass
    
    @staticmethod
    def notify_profile_updated(user):
        """Notify user that their profile was updated"""
        try:
            preferences = UserPreferences.objects.get(user=user)
            if preferences.activity_notifications:
                NotificationService.create_notification(
                    user=user,
                    notification_type='info',
                    title='Profile Updated',
                    message='Your profile information has been updated successfully.'
                )
        except UserPreferences.DoesNotExist:
            pass
    
    @staticmethod
    def notify_new_feature(feature_title, feature_description):
        """Notify all users about a new feature"""
        users = User.objects.filter(
            is_active=True,
            preferences__activity_notifications=True
        )
        
        for user in users:
            NotificationService.create_notification(
                user=user,
                notification_type='feature',
                title=f'New Feature: {feature_title}',
                message=feature_description
            )
    
    @staticmethod
    def notify_policy_update(policy_title, policy_description):
        """Notify all users about a policy update"""
        users = User.objects.filter(is_active=True)
        
        for user in users:
            # Create notification for all users (policy updates are important)
            NotificationService.create_notification(
                user=user,
                notification_type='policy',
                title=f'Policy Update: {policy_title}',
                message=policy_description
            )
            
            # Send email to users who have email notifications enabled
            try:
                preferences = UserPreferences.objects.get(user=user)
                if preferences.email_notifications:
                    NotificationService.send_email_notification(
                        user=user,
                        subject=f'Policy Update: {policy_title}',
                        message=policy_description,
                        notification_type='policy'
                    )
            except UserPreferences.DoesNotExist:
                pass
    
    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications for a user"""
        return Notification.objects.filter(user=user, is_read=False).count()
    
    @staticmethod
    def get_recent_notifications(user, limit=5):
        """Get recent notifications for a user"""
        return Notification.objects.filter(user=user)[:limit]
    
    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read for a user"""
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
