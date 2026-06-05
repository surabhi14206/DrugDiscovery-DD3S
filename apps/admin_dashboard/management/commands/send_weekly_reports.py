"""
Management command to send weekly reports to all users
Run with: python manage.py send_weekly_reports
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.admin_dashboard.services import WeeklyReportService


class Command(BaseCommand):
    help = 'Send weekly activity reports to all users who have enabled them'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting weekly report generation...'))
        self.stdout.write(f'Timestamp: {timezone.now()}')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No emails will be sent'))
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users_count = User.objects.filter(
                preferences__weekly_reports=True,
                is_active=True,
                email_verified=True
            ).count()
            self.stdout.write(f'Would send reports to {users_count} users')
            return
        
        # Send reports
        results = WeeklyReportService.send_all_weekly_reports()
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully sent: {results["sent"]}'))
        self.stdout.write(self.style.WARNING(f'⊘ Skipped (already sent): {results["skipped"]}'))
        self.stdout.write(self.style.ERROR(f'✗ Failed: {results["failed"]}'))
        
        if results['errors']:
            self.stdout.write(self.style.ERROR('\nErrors:'))
            for error in results['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Weekly report generation completed!'))
