from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Extended user model with role-based access"""
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user'
    )
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        blank=True,
        null=True,
        help_text='Profile photo'
    )
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class MoleculeViewHistory(models.Model):
    """Track which molecules users have viewed"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='molecule_views'
    )
    molecule = models.ForeignKey(
        'molecules.Molecule',
        on_delete=models.CASCADE,
        related_name='user_views'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    view_count = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'molecule_view_history'
        verbose_name = 'Molecule View History'
        verbose_name_plural = 'Molecule View Histories'
        unique_together = ('user', 'molecule')
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.molecule.name}"
