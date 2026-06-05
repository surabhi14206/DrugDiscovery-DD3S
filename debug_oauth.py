#!/usr/bin/env python
"""
Debug OAuth entries in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def debug_oauth():
    """Check all OAuth entries in detail"""
    
    print("=== OAuth Database Debug ===\n")
    
    # Check all sites
    sites = Site.objects.all()
    print(f"Sites in database: {sites.count()}")
    for site in sites:
        print(f"  - ID: {site.id}, Domain: {site.domain}, Name: {site.name}")
    
    print()
    
    # Check all SocialApp entries
    all_apps = SocialApp.objects.all()
    print(f"Total SocialApp entries: {all_apps.count()}")
    
    for app in all_apps:
        print(f"\nProvider: {app.provider}")
        print(f"  ID: {app.id}")
        print(f"  Name: {app.name}")
        print(f"  Client ID: {app.client_id[:20]}..." if app.client_id else "  Client ID: None")
        print(f"  Sites: {', '.join([s.domain for s in app.sites.all()])}")
    
    print("\n" + "="*40)
    
    # Check specifically for google
    google_apps = SocialApp.objects.filter(provider='google')
    print(f"\nGoogle apps (case-sensitive): {google_apps.count()}")
    
    # Check for case variations
    all_providers = SocialApp.objects.values_list('provider', flat=True)
    unique_providers = set(all_providers)
    print(f"\nAll unique providers: {unique_providers}")
    
    # Get current site
    current_site = Site.objects.get_current()
    print(f"\nCurrent site: {current_site.domain} (ID: {current_site.id})")
    
    # Check duplicate providers
    from collections import Counter
    provider_counts = Counter(all_providers)
    print(f"\nProvider counts:")
    for provider, count in provider_counts.items():
        status = "✗ DUPLICATE!" if count > 1 else "✓"
        print(f"  {status} {provider}: {count}")

if __name__ == '__main__':
    debug_oauth()
