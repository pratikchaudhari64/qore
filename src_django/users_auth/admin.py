from django.contrib import admin

from .models import UserProfile, Trades

admin.site.register(UserProfile)
admin.site.register(Trades)