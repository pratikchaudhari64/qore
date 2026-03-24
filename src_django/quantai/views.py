import json
import logging

from celery.result import AsyncResult
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from . import gemini_client
from .tasks import run_gemini_query

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "quantai/index.html")


@require_GET
def health(request):
    return JsonResponse({
        "status": "ok",
        "client_ready": gemini_client.is_client_ready(),
    })


@csrf_exempt
@require_POST
def submit(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    prompt = body.get("prompt", "").strip()
    if not prompt:
        return JsonResponse({"error": "prompt is required"}, status=400)

    logger.info(f"Enqueuing query: {prompt[:80]}...")
    task = run_gemini_query.delay(prompt)
    return JsonResponse({"job_id": str(task.id)})


@require_GET
def result(request, job_id):
    res = AsyncResult(job_id)
    state = res.state

    if state in ("PENDING", "STARTED", "RETRY"):
        return JsonResponse({"status": "pending"})
    elif state == "SUCCESS":
        return JsonResponse({"status": "done", "blocks": res.result})
    elif state == "FAILURE":
        return JsonResponse({"status": "error", "error": str(res.result)})
    else:
        return JsonResponse({"status": "not_found"}, status=404)
