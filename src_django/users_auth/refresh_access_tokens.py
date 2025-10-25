import os, sys
import django
from django.conf import settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

django.setup()

from users_auth.models import UserProfile
from django.contrib.auth.models import User

print(User.objects.get(id = 1).email)
print(UserProfile.objects.get(name="testuser").kite_username)
print(UserProfile.objects.get(name="testuser").kite_pwd)
print(UserProfile.objects.get(name="testuser").totp_key)