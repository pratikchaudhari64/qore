from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from users_auth.custom_fields import EncryptedField

# --- 1. USER PROFILE MODEL ---
# This model extends Django's default User model to store Kite-specific credentials.
class UserProfile(models.Model):
    """
    Stores credentials and user-specific details for interacting with the Kite API.
    All sensitive fields are marked as (encrypted) in your schema, so we assume
    they will be encrypted before storage.
    """
    # Link to Django's built-in User model
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='kite_profile'
    )
    
    # name is often covered by User.first_name/last_name, but kept here for completeness
    name = models.CharField(max_length=255, blank=True)

    # (encrypted) fields from your schema
    kite_username = EncryptedField(max_length=255, blank=False, null=False, help_text="Kite login ID (encrypted).")
    kite_pwd = EncryptedField(max_length=255, blank=False, null=False, help_text="Kite password (encrypted).")
    totp_key = EncryptedField(max_length=255, blank=True, null=True, help_text="TOTP secret key (encrypted).")
    
    # Kite api creds
    kite_api_key = EncryptedField(
        max_length=64, # Standard length for API keys
        blank=False,
        null=False, 
        help_text="The application's Kite API Key (encrypted)."
    )

    kite_api_secret = EncryptedField(
        max_length=128, # Standard length for API secrets
        blank=False,
        null=False, 
        help_text="The application's Kite API Secret (encrypted)."
    )

    # access_token used for API calls
    access_token = EncryptedField(
        max_length=512,
        help_text="The latest valid Kite Connect access token."
    )
    
    # Store API Key and Secret for generating the session
    # api_key = models.CharField(max_length=64, help_text="The application's API Key.")
    # api_secret = models.CharField(max_length=128, help_text="The application's API Secret.")

    def __str__(self):
        return f"{self.user.username}'s Kite Profile"

    class Meta:
        verbose_name = "Kite User Profile"


# --- 2. TRADES LEDGER MODEL ---
# This stores the executed trade fills retrieved from the Kite /trades endpoint.
class Trades(models.Model):
    """
    Stores an executed trade fill (a single transaction record).
    """
    # Foreign Key linking the trade back to the user who executed it
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trades',
        help_text="The user who executed this trade."
    )

    # Unique ID for the trade (Primary Key)
    # The Kite API trade_id is a big integer or string, CharField is safe.
    trade_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique trade identifier from the exchange (fill ID)."
    )

    # Core Transaction Details
    order_id = models.CharField(max_length=50, db_index=True)
    exchange_order_id = models.CharField(max_length=50)

    # Instrument Details
    tradingsymbol = models.CharField(max_length=50, db_index=True)
    instrument_token = models.CharField(max_length=50) # BigInt in Kite, CharField for safety
    exchange = models.CharField(max_length=10) # NSE, BSE, NFO, etc.
    product = models.CharField(max_length=10) # CNC, MIS, NRML, etc.

    # Financial Details
    quantity = models.IntegerField(help_text="The executed quantity (the 'fill').")
    # DecimalField is crucial for currency/price to prevent floating point errors
    average_price = models.DecimalField(max_digits=12, decimal_places=4)
    transaction_type = models.CharField(max_length=12) # BUY or SELL
    
    # Kite has other fields like 'price', 'trigger_price', but 'average_price' is key for the ledger
    
    # Timestamps (Crucial for time-series analysis)
    # fill_timestamp is the accurate execution time we discussed
    fill_timestamp = models.DateTimeField(
        db_index=True, 
        help_text="The precise execution time of the trade (the fill time)."
    )
    
    # Storing other timestamps for reference/debugging
    order_timestamp = models.DateTimeField(null=True, blank=True)
    exchange_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Meta
    tag = models.CharField(max_length=255, blank=True, null=True, help_text="Optional user-defined tag.")


    def __str__(self):
        return f"{self.user.username}: {self.tradingsymbol} {self.transaction_type} {self.quantity} @ {self.average_price} ({self.fill_timestamp.date()})"

    class Meta:
        verbose_name_plural = "Trades"
        # Index on the most common lookup combination: symbol and time
        indexes = [
            models.Index(fields=['tradingsymbol', 'fill_timestamp']),
        ]
        # Ensure we don't accidentally insert the same trade twice
        unique_together = ('trade_id', 'user',)