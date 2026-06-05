"""
Forms for user management in admin dashboard
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class AddUserForm(forms.ModelForm):
    """Form for adding a new user in admin dashboard"""
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        help_text='Password must be at least 8 characters'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name (optional)'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name (optional)'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'is_staff': 'Admin Access',
            'is_active': 'Active Account',
        }
        help_texts = {
            'username': 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
            'is_staff': 'User can access admin dashboard',
            'is_active': 'User can log in to the system',
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Passwords don't match")
            try:
                validate_password(password2)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
        
        return user


class EditUserForm(forms.ModelForm):
    """Form for editing existing user in admin dashboard"""
    
    change_password = forms.BooleanField(
        required=False,
        label='Change Password',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    new_password1 = forms.CharField(
        required=False,
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        required=False,
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'email_verified']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name (optional)'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name (optional)'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'is_staff': 'Admin Access',
            'is_active': 'Active Account',
            'email_verified': 'Email Verified',
        }
        help_texts = {
            'username': 'Required. 150 characters or fewer.',
            'is_staff': 'User can access admin dashboard',
            'is_active': 'User can log in to the system',
            'email_verified': 'Email address has been verified',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        change_password = cleaned_data.get('change_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if change_password:
            if not new_password1:
                raise ValidationError({'new_password1': 'Password is required when changing password'})
            if not new_password2:
                raise ValidationError({'new_password2': 'Please confirm the new password'})
            if new_password1 != new_password2:
                raise ValidationError({'new_password2': "Passwords don't match"})
            try:
                validate_password(new_password1)
            except ValidationError as e:
                raise ValidationError({'new_password1': e.messages})
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if self.cleaned_data.get('change_password'):
            user.set_password(self.cleaned_data['new_password1'])
        
        if commit:
            user.save()
        
        return user
