"""
Send sample notifications and weekly reports to all users
Run with: python send_sample_emails.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import CustomUser
from apps.admin_dashboard.notification_service import NotificationService
from apps.admin_dashboard.services import WeeklyReportService
from apps.admin_dashboard.models import UserPreferences

def send_sample_emails():
    print("=" * 70)
    print("SENDING SAMPLE EMAILS TO ALL USERS")
    print("=" * 70)
    
    # Get all active users with verified emails
    users = CustomUser.objects.filter(is_active=True)
    
    if not users.exists():
        print("❌ No users found in the database.")
        return
    
    print(f"\n✓ Found {users.count()} user(s)")
    
    for user in users:
        print(f"\n{'=' * 70}")
        print(f"Processing user: {user.username} ({user.email})")
        print("=" * 70)
        
        # Ensure user has preferences
        preferences, created = UserPreferences.objects.get_or_create(
            user=user,
            defaults={
                'email_notifications': True,
                'activity_notifications': True,
                'weekly_reports': True
            }
        )
        
        if created:
            print(f"✓ Created preferences for {user.username}")
        
        print(f"\nUser preferences:")
        print(f"  - Email Notifications: {preferences.email_notifications}")
        print(f"  - Activity Notifications: {preferences.activity_notifications}")
        print(f"  - Weekly Reports: {preferences.weekly_reports}")
        
        # 1. Send sample activity notification email
        print(f"\n📧 Sending sample activity notification email...")
        success, message = NotificationService.send_email_notification(
            user=user,
            subject='Welcome to DD3S Notification System!',
            message=f'''Hello {user.username},

This is a sample notification to demonstrate our email notification system.

Your account now has access to:
• Real-time popup notifications on the website
• Email alerts for important activities
• Weekly activity summary reports

You can manage these preferences anytime from your Profile → Notification Settings.

Thank you for using DD3S Molecular Database!''',
            notification_type='info'
        )
        
        if success:
            print(f"   ✓ Activity notification email sent successfully!")
        else:
            print(f"   ❌ Failed: {message}")
        
        # 2. Create popup notification
        print(f"\n📲 Creating popup notification...")
        if preferences.activity_notifications:
            notification = NotificationService.create_notification(
                user=user,
                notification_type='feature',
                title='Notification System Active',
                message='Your notification system is now active! You will receive updates here.'
            )
            print(f"   ✓ Popup notification created (ID: {notification.id})")
        else:
            print(f"   ⊘ Skipped - Activity notifications disabled")
        
        # 3. Send sample weekly report
        print(f"\n📊 Sending sample weekly report...")
        if preferences.weekly_reports:
            success, message = WeeklyReportService.send_weekly_report(user)
            if success:
                print(f"   ✓ Weekly report sent successfully!")
            else:
                print(f"   ⊘ {message}")
        else:
            print(f"   ⊘ Skipped - Weekly reports disabled")
        
        # 4. Send password change notification (sample)
        print(f"\n🔐 Sending sample security alert...")
        success, message = NotificationService.send_email_notification(
            user=user,
            subject='Security Alert - Sample Notification',
            message=f'''Hello {user.username},

This is a sample security notification.

In real scenarios, you would receive notifications for:
• New login from different device/location
• Password changes
• Two-factor authentication changes
• Profile updates
• Data exports

This helps keep your account secure by alerting you of any suspicious activity.

If you ever receive a notification about an activity you didn't perform, please contact support immediately at dd3s.sup@gmail.com.''',
            notification_type='warning'
        )
        
        if success:
            print(f"   ✓ Security alert email sent successfully!")
        else:
            print(f"   ❌ Failed: {message}")
    
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Processed {users.count()} user(s)")
    print(f"\nEmails sent to:")
    for user in users:
        print(f"  • {user.username} - {user.email}")
    
    print(f"\n{'=' * 70}")
    print("WHAT TO CHECK NOW:")
    print("=" * 70)
    print("1. Check your email inbox for the following emails:")
    print("   - Welcome to DD3S Notification System")
    print("   - Weekly Activity Report")
    print("   - Security Alert Sample")
    print("\n2. Log in to the website and check for popup notifications")
    print("\n3. Go to Profile → Notification Settings to manage preferences")
    print("\n4. Check spam/junk folder if emails are not in inbox")
    print("=" * 70)

if __name__ == '__main__':
    try:
        send_sample_emails()
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
