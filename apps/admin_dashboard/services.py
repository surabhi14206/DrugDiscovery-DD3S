"""
Weekly Report Email Service
Generates and sends weekly activity reports to users
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from apps.admin_dashboard.models import WeeklyReport, UserPreferences
from apps.molecules.models import Molecule

User = get_user_model()


class WeeklyReportService:
    """Service to generate and send weekly reports"""
    
    @staticmethod
    def get_week_dates():
        """Get start and end dates for the previous week"""
        today = timezone.now().date()
        week_end = today - timedelta(days=today.weekday() + 1)  # Last Sunday
        week_start = week_end - timedelta(days=6)  # Previous Monday
        return week_start, week_end
    
    @staticmethod
    def generate_user_statistics(user, week_start, week_end):
        """Generate statistics for a user for the given week"""
        from apps.admin_dashboard.models import UserActivity
        
        # Get activities for the week
        activities = UserActivity.objects.filter(
            user=user,
            timestamp__date__gte=week_start,
            timestamp__date__lte=week_end
        )
        
        # Count different activity types
        total_activities = activities.count()
        
        # Get molecule-related activities
        molecule_views = activities.filter(action_type='page_view').count()
        
        # Get search activities
        searches = activities.filter(action_type='search').count()
        
        # Count predictions (if you have this tracked)
        predictions = 0  # Placeholder - add actual prediction tracking
        
        return {
            'total_activities': total_activities,
            'molecules_viewed': molecule_views,
            'predictions_made': predictions,
            'searches_performed': searches,
            'week_start': week_start,
            'week_end': week_end,
        }
    
    @staticmethod
    def get_platform_updates():
        """Get recent platform updates and features (curated, safe information)"""
        return [
            {
                'type': 'feature',
                'title': 'Enhanced Molecule Visualization',
                'description': 'Improved 3D rendering and interaction capabilities for molecular structures.',
            },
            {
                'type': 'update',
                'title': 'Security Enhancements',
                'description': 'Two-factor authentication and email verification for better account security.',
            },
            {
                'type': 'feature',
                'title': 'Activity Notifications',
                'description': 'Real-time notifications keep you updated on your account activities.',
            },
        ]
    
    @staticmethod
    def get_policy_updates():
        """Get recent policy updates (if any)"""
        # Return empty list for now - add policy updates manually as needed
        return []
    
    @staticmethod
    def send_weekly_report(user):
        """Generate and send weekly report to a user"""
        # Check if user wants weekly reports
        try:
            preferences = UserPreferences.objects.get(user=user)
            if not preferences.weekly_reports:
                return False, "User has disabled weekly reports"
        except UserPreferences.DoesNotExist:
            return False, "No preferences found for user"
        
        # Get week dates
        week_start, week_end = WeeklyReportService.get_week_dates()
        
        # Check if report already sent for this week
        existing_report = WeeklyReport.objects.filter(
            user=user,
            week_start=week_start
        ).first()
        
        if existing_report:
            return False, f"Report already sent for week {week_start}"
        
        # Generate statistics
        stats = WeeklyReportService.generate_user_statistics(user, week_start, week_end)
        
        # Get platform updates and policies
        platform_updates = WeeklyReportService.get_platform_updates()
        policy_updates = WeeklyReportService.get_policy_updates()
        
        # Prepare email context
        context = {
            'user': user,
            'stats': stats,
            'platform_updates': platform_updates,
            'policy_updates': policy_updates,
            'week_start': week_start,
            'week_end': week_end,
            'support_email': 'dd3s.sup@gmail.com',
        }
        
        # Render email template
        html_message = render_to_string('admin_dashboard/emails/weekly_report.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        try:
            send_mail(
                subject=f'Your Weekly Activity Report - {week_start.strftime("%b %d")} to {week_end.strftime("%b %d, %Y")}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Create report record
            WeeklyReport.objects.create(
                user=user,
                week_start=week_start,
                week_end=week_end,
                total_activities=stats['total_activities'],
                molecules_viewed=stats['molecules_viewed'],
                predictions_made=stats['predictions_made'],
                searches_performed=stats['searches_performed'],
            )
            
            return True, "Weekly report sent successfully"
            
        except Exception as e:
            return False, f"Error sending email: {str(e)}"
    
    @staticmethod
    def send_all_weekly_reports():
        """Send weekly reports to all users who have enabled them"""
        users_with_reports = User.objects.filter(
            preferences__weekly_reports=True,
            is_active=True,
            email_verified=True
        )
        
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        for user in users_with_reports:
            success, message = WeeklyReportService.send_weekly_report(user)
            if success:
                results['sent'] += 1
            elif 'already sent' in message.lower():
                results['skipped'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"{user.email}: {message}")
        
        return results
