#!/usr/bin/env python
"""
Fix duplicate SocialApp entries in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def fix_duplicate_oauth():
    """Remove duplicate OAuth provider entries"""
    
    print("=== Fixing Duplicate OAuth Entries ===\n")
    
    # Get current site
    site = Site.objects.get_current()
    
    # Check Google apps
    google_apps = SocialApp.objects.filter(provider='google')
    print(f"Found {google_apps.count()} Google OAuth entries")
    
    if google_apps.count() > 1:
        print("Removing duplicates...")
        # Keep the first one, delete the rest
        keep_app = google_apps.first()
        google_apps.exclude(id=keep_app.id).delete()
        print(f"✓ Kept 1 Google OAuth entry (ID: {keep_app.id})")
        
        # Ensure it's linked to the site
        if site not in keep_app.sites.all():
            keep_app.sites.add(site)
            print(f"✓ Linked to site: {site.domain}")
    elif google_apps.count() == 1:
        print("✓ Only 1 Google OAuth entry found (correct)")
    else:
        print("✗ No Google OAuth entries found - run setup_oauth.py")
    
    print()
    
    # Check GitHub apps
    github_apps = SocialApp.objects.filter(provider='github')
    print(f"Found {github_apps.count()} GitHub OAuth entries")
    
    if github_apps.count() > 1:
        print("Removing duplicates...")
        # Keep the first one, delete the rest
        keep_app = github_apps.first()
        github_apps.exclude(id=keep_app.id).delete()
        print(f"✓ Kept 1 GitHub OAuth entry (ID: {keep_app.id})")
        
        # Ensure it's linked to the site
        if site not in keep_app.sites.all():
            keep_app.sites.add(site)
            print(f"✓ Linked to site: {site.domain}")
    elif github_apps.count() == 1:
        print("✓ Only 1 GitHub OAuth entry found (correct)")
    else:
        print("✗ No GitHub OAuth entries found")
    
    print("\n=== Fix Complete ===")
    print("\n✓ Restart your Django server and try Google login again!")

if __name__ == '__main__':
    fix_duplicate_oauth()
