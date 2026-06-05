import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import CustomUser

print("\n" + "="*60)
print("USER EMAIL STATUS CHECK")
print("="*60)

users = CustomUser.objects.all()

if not users:
    print("\nNo users found in database!")
else:
    for user in users:
        print(f"\n📧 Username: {user.username}")
        print(f"   Email: {'[NO EMAIL SET]' if not user.email else user.email}")
        print(f"   Email Verified: {'✅ Yes' if user.email_verified else '❌ No'}")
        print(f"   2FA Enabled: {'✅ Yes' if user.two_factor_enabled else '❌ No'}")

print("\n" + "="*60)
print("\nIMPORTANT NOTES:")
print("- Email verification requires a valid email address")
print("- Currently using console email backend (emails print to terminal)")
print("- Check the terminal/console output when clicking 'Verify Email'")
print("="*60 + "\n")
