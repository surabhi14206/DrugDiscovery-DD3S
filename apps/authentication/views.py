from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Max
from django.core.files.storage import default_storage
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
import os
from .models import CustomUser, MoleculeViewHistory
from .forms import UserRegistrationForm, UserLoginForm


@never_cache
@csrf_protect
def auth_view(request):
    """Combined login/register view"""
    login_form = UserLoginForm()
    registration_form = UserRegistrationForm()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'login':
            # Handle login with CAPTCHA
            login_form = UserLoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, 'Successfully logged in!')
                    return redirect('visualization:home')
                else:
                    messages.error(request, 'Invalid credentials')
            else:
                for field, errors in login_form.errors.items():
                    for error in errors:
                        if field == 'captcha':
                            messages.error(request, 'Please verify you are human')
                        else:
                            messages.error(request, f'{field}: {error}')
                
        elif form_type == 'register':
            # Handle registration with CAPTCHA
            registration_form = UserRegistrationForm(request.POST)
            if registration_form.is_valid():
                try:
                    user = registration_form.save(commit=False)
                    user.is_active = True
                    user.save()
                    
                    login(request, user)
                    messages.success(request, 'Registration successful!')
                    return redirect('visualization:home')
                except Exception as e:
                    messages.error(request, f'Error during registration: {str(e)}')
            else:
                for field, errors in registration_form.errors.items():
                    for error in errors:
                        if field == 'captcha':
                            messages.error(request, 'Please verify you are human')
                        else:
                            messages.error(request, f'{field}: {error}')
        
        # Return to auth page with forms
        return render(request, 'authentication/auth.html', {
            'form_type': form_type,
            'login_form': login_form,
            'registration_form': registration_form
        })
    
    return render(request, 'authentication/auth.html', {
        'login_form': login_form,
        'registration_form': registration_form
    })


def register(request):
    """Legacy registration view - redirects to combined auth"""
    return redirect('authentication:auth')


def login_view(request):
    """Legacy login view - redirects to combined auth"""
    return redirect('authentication:auth')


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'Successfully logged out')
    return redirect('visualization:home')


def terms_and_conditions(request):
    """Terms and conditions page"""
    return render(request, 'authentication/terms.html')


@login_required
def profile(request):
    """User profile view"""
    return render(request, 'authentication/profile.html', {
        'user': request.user
    })


@login_required
def user_dashboard(request):
    """Personal dashboard showing molecule viewing history"""
    # Get user's molecule viewing history
    view_history = MoleculeViewHistory.objects.filter(
        user=request.user
    ).select_related('molecule').order_by('-viewed_at')[:50]  # Last 50 views
    
    # Get statistics
    total_views = view_history.aggregate(total=Count('id'))['total'] or 0
    unique_molecules = MoleculeViewHistory.objects.filter(
        user=request.user
    ).values('molecule').distinct().count()
    
    # Get most viewed molecules
    most_viewed = MoleculeViewHistory.objects.filter(
        user=request.user
    ).values(
        'molecule__id',
        'molecule__name',
        'molecule__pdb_id',
        'molecule__smiles'
    ).annotate(
        total_views=Count('id'),
        last_viewed=Max('viewed_at')
    ).order_by('-total_views')[:10]
    
    context = {
        'view_history': view_history,
        'total_views': total_views,
        'unique_molecules': unique_molecules,
        'most_viewed': most_viewed,
    }
    
    return render(request, 'authentication/dashboard.html', context)


@login_required
def upload_profile_photo(request):
    """Handle profile photo upload"""
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        photo = request.FILES['profile_photo']
        
        # Validate file size (5MB max)
        if photo.size > 5 * 1024 * 1024:
            messages.error(request, 'File size must be less than 5MB.')
            return redirect('authentication:profile')
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/jpg']
        if photo.content_type not in allowed_types:
            messages.error(request, 'Only JPG, PNG, and GIF images are allowed.')
            return redirect('authentication:profile')
        
        # Delete old photo if exists
        if request.user.profile_photo:
            old_photo_path = request.user.profile_photo.path
            if os.path.exists(old_photo_path):
                os.remove(old_photo_path)
        
        # Save new photo
        request.user.profile_photo = photo
        request.user.save()
        
        messages.success(request, 'Profile photo updated successfully!')
    else:
        messages.error(request, 'Please select a photo to upload.')
    
    return redirect('authentication:profile')


def csrf_failure(request, reason=""):
    """Custom CSRF failure view"""
    # If user is already authenticated, redirect to home instead of auth page
    if request.user.is_authenticated:
        messages.warning(request, 'Session expired. Please refresh the page.')
        return redirect('visualization:home')
    
    messages.error(request, 'Security token expired. Please try again.')
    return redirect('authentication:auth')


# Email Verification Views
@login_required
def send_verification_email(request):
    """Send email verification link to user"""
    from django.core.mail import send_mail
    from django.urls import reverse
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    
    if request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('authentication:profile')
    
    # Generate verification token
    token = default_token_generator.make_token(request.user)
    uid = urlsafe_base64_encode(force_bytes(request.user.pk))
    
    # Build verification URL
    verification_url = request.build_absolute_uri(
        reverse('authentication:verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    
    # Send email
    subject = f'{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}Verify Your Email Address'
    message = f"""
    Hello {request.user.username},
    
    Please click the link below to verify your email address:
    {verification_url}
    
    This link will expire in 5 minutes.
    
    If you didn't request this verification, please ignore this email.
    
    Best regards,
    DD3S Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        messages.success(request, f'Verification email sent to {request.user.email}')
    except Exception as e:
        messages.error(request, f'Failed to send verification email: {str(e)}')
    
    return redirect('authentication:profile')


def verify_email(request, uidb64, token):
    """Verify email address using token"""
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save()
        messages.success(request, 'Email verified successfully!')
        return redirect('authentication:login' if not request.user.is_authenticated else 'authentication:profile')
    else:
        messages.error(request, 'Verification link is invalid or has expired.')
        return redirect('authentication:login')


# Two-Factor Authentication Views
@login_required
def setup_2fa(request):
    """Display QR code for 2FA setup"""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.util import random_hex
    import qrcode
    import io
    import base64
    
    if request.user.two_factor_enabled:
        messages.info(request, '2FA is already enabled for your account.')
        return redirect('authentication:profile')
    
    # Check if user wants to regenerate
    regenerate = request.GET.get('regenerate', None)
    
    # Get or create TOTP device
    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    
    if regenerate or not device:
        # Delete old unconfirmed devices and create new one
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
        device = TOTPDevice.objects.create(
            user=request.user,
            name='default',
            confirmed=False,
        )
        if regenerate:
            messages.info(request, 'New QR code generated. Please scan the updated code.')
    
    # Generate QR code
    url = device.config_url
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Format secret key for better readability (groups of 4)
    secret_key = device.key
    formatted_key = ' '.join([secret_key[i:i+4] for i in range(0, len(secret_key), 4)])
    
    context = {
        'qr_code': qr_code_base64,
        'secret_key': formatted_key,
        'secret_key_raw': secret_key,
        'device': device,
    }
    
    return render(request, 'authentication/setup_2fa.html', context)


@login_required
def verify_2fa_setup(request):
    """Verify 2FA setup with user-provided token"""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    
    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            messages.error(request, 'No 2FA setup found. Please start setup again.')
            return redirect('authentication:setup_2fa')
        
        # Verify token
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            
            request.user.two_factor_enabled = True
            request.user.save()
            
            messages.success(request, '2FA enabled successfully!')
            return redirect('authentication:profile')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')
            return redirect('authentication:setup_2fa')
    
    return redirect('authentication:setup_2fa')


@login_required
def disable_2fa(request):
    """Disable 2FA for user account"""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    
    if request.method == 'POST':
        # Delete all TOTP devices for user
        TOTPDevice.objects.filter(user=request.user).delete()
        
        request.user.two_factor_enabled = False
        request.user.save()
        
        messages.success(request, '2FA has been disabled for your account.')
        return redirect('authentication:profile')
    
    return render(request, 'authentication/disable_2fa.html')
