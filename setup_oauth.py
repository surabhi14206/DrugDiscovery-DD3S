#!/usr/bin/env python
"""
Quick setup script for OAuth Social Applications in Django admin.
Run this after you've added your credentials to .env file.

Usage:
    python setup_oauth.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_site():
    """Configure the Django site."""
    site, created = Site.objects.get_or_create(
        id=1,
        defaults={
            'domain': '127.0.0.1:8000',
            'name': 'DD3S'
        }
    )
    if not created:
        site.domain = '127.0.0.1:8000'
        site.name = 'DD3S'
        site.save()
    
    print(f"✓ Site configured: {site.domain}")
    return site

def setup_google_oauth(site):
    """Setup Google OAuth application."""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    if not client_id or client_id == 'your-google-client-id-here':
        print("✗ Google OAuth: Missing credentials in .env file")
        print("  Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env")
        return None
    
    app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google OAuth',
            'client_id': client_id,
            'secret': client_secret,
        }
    )
    
    if not created:
        app.name = 'Google OAuth'
        app.client_id = client_id
        app.secret = client_secret
        app.save()
    
    # Add site to the app
    if site not in app.sites.all():
        app.sites.add(site)
    
    print(f"✓ Google OAuth configured")
    return app

def setup_github_oauth(site):
    """Setup GitHub OAuth application."""
    client_id = os.getenv('GITHUB_CLIENT_ID', '')
    client_secret = os.getenv('GITHUB_CLIENT_SECRET', '')
    
    if not client_id or client_id == 'your-github-client-id-here':
        print("✗ GitHub OAuth: Missing credentials in .env file")
        print("  Please add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to .env")
        return None
    
    app, created = SocialApp.objects.get_or_create(
        provider='github',
        defaults={
            'name': 'GitHub OAuth',
            'client_id': client_id,
            'secret': client_secret,
        }
    )
    
    if not created:
        app.name = 'GitHub OAuth'
        app.client_id = client_id
        app.secret = client_secret
        app.save()
    
    # Add site to the app
    if site not in app.sites.all():
        app.sites.add(site)
    
    print(f"✓ GitHub OAuth configured")
    return app

def main():
    print("\n=== OAuth Setup ===\n")
    
    # Setup site
    site = setup_site()
    
    # Setup OAuth providers
    google_app = setup_google_oauth(site)
    github_app = setup_github_oauth(site)
    
    print("\n=== Setup Complete ===\n")
    
    if not google_app and not github_app:
        print("⚠ No OAuth providers configured!")
        print("\nNext steps:")
        print("1. Get OAuth credentials from Google/GitHub")
        print("2. Add them to .env file")
        print("3. Run this script again: python setup_oauth.py")
        print("\nSee SETUP_GOOGLE_OAUTH.md for detailed instructions")
    else:
        print("✓ OAuth providers are ready!")
        print("\nYou can now:")
        print("1. Restart your Django server")
        print("2. Visit: http://127.0.0.1:8000/accounts/login/")
        print("3. Click 'Continue with Google' or 'Continue with GitHub'")
        
        if not google_app:
            print("\n⚠ Google OAuth not configured (add credentials to .env)")
        if not github_app:
            print("⚠ GitHub OAuth not configured (add credentials to .env)")

if __name__ == '__main__':
    main()
