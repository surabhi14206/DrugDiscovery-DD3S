import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("\n" + "="*60)
print("EMAIL CONFIGURATION TEST")
print("="*60)

print(f"\n📧 Email Backend: {settings.EMAIL_BACKEND}")
print(f"📧 Email Host: {settings.EMAIL_HOST}")
print(f"📧 Email Port: {settings.EMAIL_PORT}")
print(f"📧 Email Use TLS: {settings.EMAIL_USE_TLS}")
print(f"📧 Email User: {settings.EMAIL_HOST_USER}")
print(f"📧 Email Password: {'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
print(f"📧 Default From: {settings.DEFAULT_FROM_EMAIL}")

print("\n" + "="*60)
print("SENDING TEST EMAIL...")
print("="*60)

try:
    send_mail(
        subject='Test Email from DD3S',
        message='If you receive this email, your email configuration is working correctly!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['yadavsurabhi14206@gmail.com'],
        fail_silently=False,
    )
    print("\n✅ SUCCESS! Test email sent successfully!")
    print("📬 Check your inbox: yadavsurabhi14206@gmail.com")
    print("📁 Also check your SPAM/JUNK folder")
    
except Exception as e:
    print(f"\n❌ ERROR: Failed to send email")
    print(f"Error details: {str(e)}")
    print("\nPossible issues:")
    print("1. App password might be incorrect")
    print("2. Gmail account needs 2-Step Verification enabled")
    print("3. Network/firewall blocking SMTP connection")
    print("4. Check if 'Less secure app access' is needed (deprecated)")

print("\n" + "="*60 + "\n")
