from django.shortcuts import render
from django.http import HttpResponse, HttpRequest

# Create your views here.
def root(request):
    return HttpResponse("Hello, world. You're at the market_data root.")