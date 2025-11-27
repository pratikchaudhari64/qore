from django.db import models
# from django.contrib.auth.models import User
from django.utils import timezone
from users_auth.custom_fields import EncryptedField

class APICredentials(models.Model):
    """
    Stores API credentials for various data providers (Dhan, etc.)
    All sensitive fields are encrypted.
    """
    
    # API provider name (e.g., 'dhan', 'zerodha', 'upstox')
    provider = models.CharField(
        max_length=50,
        unique=True,
        help_text="API provider name (e.g., 'dhan', 'zerodha')"
    )
    
    # Encrypted fields
    api_key = EncryptedField(
        max_length=255,
        blank=True,
        null=True,
        help_text="API Key (encrypted)"
    )
    
    api_secret = EncryptedField(
        max_length=255,
        blank=True,
        null=True,
        help_text="API Secret (encrypted)"
    )
    
    access_token = EncryptedField(
        max_length=512,
        blank=True,
        null=True,
        help_text="Access token (encrypted)"
    )
    
    totp_secret = EncryptedField(
        max_length=255,
        blank=True,
        null=True,
        help_text="TOTP secret key (encrypted)"
    )
    
    # Metadata stored as JSON
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional metadata (createTime, expiryTime, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.provider}"
    
    class Meta:
        verbose_name = "API Credential"
        verbose_name_plural = "API Credentials"
        ordering = ['provider']