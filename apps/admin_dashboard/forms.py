from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with styled fields"""
    
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        })
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )


class UserPreferencesForm(forms.Form):
    """Form for user preferences and settings"""
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto (System)'),
    ]
    
    theme = forms.ChoiceField(
        choices=THEME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    activity_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    weekly_reports = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    two_factor_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class DataExportForm(forms.Form):
    """Form for exporting user data"""
    
    DATA_TYPE_CHOICES = [
        ('all', 'All Data'),
        ('activities', 'Activity History'),
        ('searches', 'Search History'),
        ('predictions', 'Prediction History'),
        ('molecules', 'Viewed Molecules'),
    ]
    
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('excel', 'Excel (XLSX)'),
    ]
    
    data_type = forms.ChoiceField(
        choices=DATA_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Data Type"
    )
    
    export_format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Export Format"
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="From Date (Optional)"
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="To Date (Optional)"
    )
