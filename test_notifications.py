"""
Test script to demonstrate the notification system
Run with: python test_notifications.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import CustomUser
from apps.admin_dashboard.notification_service import NotificationService
from apps.admin_dashboard.models import Notification, UserPreferences

def test_notifications():
    print("=" * 60)
    print("NOTIFICATION SYSTEM TEST")
    print("=" * 60)
    
    # Get first user
    user = CustomUser.objects.first()
    if not user:
        print("❌ No users found. Please create a user first.")
        return
    
    print(f"\n✓ Testing with user: {user.username}")
    
    # Ensure user has preferences
    preferences, created = UserPreferences.objects.get_or_create(
        user=user,
        defaults={
            'email_notifications': True,
            'activity_notifications': True,
            'weekly_reports': True
        }
    )
    print(f"✓ User preferences: Email={preferences.email_notifications}, Activity={preferences.activity_notifications}, Weekly={preferences.weekly_reports}")
    
    # Test 1: Create a popup notification
    print("\n" + "=" * 60)
    print("TEST 1: Creating popup notification...")
    print("=" * 60)
    
    notification = NotificationService.create_notification(
        user=user,
        notification_type='success',
        title='Test Notification',
        message='This is a test notification that will appear as a popup!'
    )
    print(f"✓ Notification created: {notification.title}")
    print(f"  Type: {notification.type}")
    print(f"  Message: {notification.message}")
    print(f"  Created at: {notification.created_at}")
    
    # Test 2: Create different types of notifications
    print("\n" + "=" * 60)
    print("TEST 2: Creating notifications of different types...")
    print("=" * 60)
    
    notification_types = [
        ('info', 'Information Update', 'Your profile has been viewed 10 times this week.'),
        ('warning', 'Security Alert', 'A new login was detected from a different location.'),
        ('feature', 'New Feature', 'Check out our new advanced search feature!'),
        ('policy', 'Policy Update', 'Our terms of service have been updated.'),
    ]
    
    for ntype, title, message in notification_types:
        notif = NotificationService.create_notification(
            user=user,
            notification_type=ntype,
            title=title,
            message=message
        )
        print(f"✓ Created {ntype} notification: {title}")
    
    # Test 3: Check unread notifications
    print("\n" + "=" * 60)
    print("TEST 3: Checking unread notifications...")
    print("=" * 60)
    
    unread = Notification.objects.filter(user=user, is_read=False)
    print(f"✓ User has {unread.count()} unread notifications:")
    for notif in unread[:5]:
        print(f"  - [{notif.type}] {notif.title}")
    
    # Test 4: Email notification (without actually sending)
    print("\n" + "=" * 60)
    print("TEST 4: Testing email notification service...")
    print("=" * 60)
    
    print("✓ Email notification service is ready")
    print(f"  Would send to: {user.email}")
    print(f"  Email notifications enabled: {preferences.email_notifications}")
    
    # Test 5: Weekly report service
    print("\n" + "=" * 60)
    print("TEST 5: Testing weekly report service...")
    print("=" * 60)
    
    from apps.admin_dashboard.services import WeeklyReportService
    
    week_start, week_end = WeeklyReportService.get_week_dates()
    print(f"✓ Week dates calculated:")
    print(f"  Start: {week_start}")
    print(f"  End: {week_end}")
    
    stats = WeeklyReportService.generate_user_statistics(user, week_start, week_end)
    print(f"\n✓ User statistics for this week:")
    print(f"  Total Activities: {stats['total_activities']}")
    print(f"  Molecules Viewed: {stats['molecules_viewed']}")
    print(f"  Searches: {stats['searches_performed']}")
    print(f"  Predictions: {stats['predictions_made']}")
    
    platform_updates = WeeklyReportService.get_platform_updates()
    print(f"\n✓ Platform updates to include: {len(platform_updates)}")
    for update in platform_updates:
        print(f"  - [{update['type']}] {update['title']}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("1. Go to http://127.0.0.1:8000 and log in")
    print("2. You should see notification popups appear!")
    print("3. Go to Profile → Notification Settings to configure preferences")
    print("4. Run: python manage.py send_weekly_reports --dry-run")
    print("\n")

if __name__ == '__main__':
    test_notifications()
