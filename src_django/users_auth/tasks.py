# from datetime import datetime
from django.utils import timezone
from celery import shared_task
import requests
from users_auth import refresh_access_tokens, kite_trades

@shared_task
def refresh_user_access_tokens():
    """Perform daily refresh of user access tokens"""
    successes, errors = refresh_access_tokens.run_refresh()
    
    print(f"Access tokens refreshed for {len(successes)} users: {successes}")
    print(f"Access token refresh failed for {len(errors)} users: {errors}")
    return {
        'status': 'completed',
        'timestamp': timezone.now().isoformat(),
        'success_count': len(successes),
        'error_count': len(errors),
        'successful_users': successes,
        'failed_users': errors,
    }

@shared_task
def fetch_daily_kite_trades():
    successes, errors = kite_trades.fetch_trades()

    return {
        'status': 'completed',
        'timestamp': timezone.now().isoformat(),
        'success_count': len(successes),
        'error_count': len(errors),
        'successful_users': successes,
        'failed_users': errors,
    }
