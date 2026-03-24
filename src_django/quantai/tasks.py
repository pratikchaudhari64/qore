from celery import shared_task

from . import gemini_client


@shared_task
def run_gemini_query(prompt: str):
    return gemini_client.query_gemini(prompt)
