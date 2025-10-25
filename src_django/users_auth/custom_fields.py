import base64
from django.db import models
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet, InvalidToken

# The encryption key will be read from settings.
# We create a function to fetch the Fernet instance for thread-safety and configuration.
_fernet = None

def get_fernet():
    """Fetches and initializes the Fernet instance from Django settings."""
    global _fernet
    if _fernet is None:
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ImproperlyConfigured(
                "The 'ENCRYPTION_KEY' setting must be defined for EncryptedField."
            )
        try:
            # Fernet key must be 32 url-safe base64-encoded bytes.
            _fernet = Fernet(key.encode('utf-8'))
        except Exception as e:
            raise ImproperlyConfigured(f"Invalid ENCRYPTION_KEY format: {e}")
    return _fernet

class EncryptedField(models.TextField):
    """
    A custom model field that transparently encrypts and decrypts text
    data using Fernet symmetric encryption. Stores data as a TextField.
    """
    def __init__(self, *args, **kwargs):
        # We always want the underlying database field to be large enough
        # to hold the encrypted, base64-encoded text.
        kwargs['blank'] = kwargs.get('blank', True)
        kwargs['null'] = kwargs.get('null', False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Converts the database value (ciphertext) into a Python object (plaintext)."""
        if value is None or value == '':
            return value

        if isinstance(value, str):
            # If it's already a string, it means it's coming from the database.
            try:
                f = get_fernet()
                # Encrypted text in DB is base64 encoded, which Fernet expects
                # in bytes format.
                decrypted_bytes = f.decrypt(value.encode('utf-8'))
                return decrypted_bytes.decode('utf-8')
            except InvalidToken:
                # Handle cases where the decryption fails (e.g., wrong key, tampered data)
                # You may want to log this error!
                print("WARNING: Could not decrypt data. Invalid Fernet token.")
                return value # Or raise an exception, depending on your policy
            except Exception:
                # Value may be unencrypted or a raw string if assigned directly
                # to the model instance before saving for the first time.
                return value
        
        return value

    def get_db_prep_save(self, value, connection):
        """Converts the Python object (plaintext) into a database value (ciphertext)."""
        if value is None or value == '':
            return super().get_db_prep_save(value, connection)
        
        # If the value is already encrypted (i.e., it's bytes from a previous
        # decryption or is already a long string of ciphertext), skip re-encryption.
        if isinstance(value, str):
            f = get_fernet()
            # Encrypt the plaintext and encode to a string for storage in TextField
            encrypted_bytes = f.encrypt(value.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        
        # Pass the result to the parent class for final preparation (e.g., string conversion)
        return super().get_db_prep_save(value, connection)

    def from_db_value(self, value, expression, connection):
        """Required for newer Django versions when retrieving values from the DB."""
        return self.to_python(value)
