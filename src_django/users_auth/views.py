from django.shortcuts import render
from django.http import HttpResponse, HttpRequest

# Create your views here.
def root(request):
    return HttpResponse("Hello, world. You're at the users_auth root.")

def kite_redirect_handler(request: HttpRequest) -> HttpResponse:
    # The request token will be in the query parameters
    redirect_status = request.GET.get('status') 
    request_token = request.GET.get('request_token')

    # print(f"request token received: {request}")
    return HttpResponse(f"redirect status: {redirect_status}")
    # if request_token:
    #     # TODO: Use the request_token to generate the session
    #     # and store the access token for the user.

    #     # Example:
    #     # kite = KiteConnect(api_key="your_api_key")
    #     # data = kite.generate_session(request_token, api_secret="your_api_secret")

    #     return HttpResponse(f"Successfully received token: {request_token}. Proceeding to finalize login...")
    # else:
    #     # Handle error/denial cases
    #     status = request.GET.get('status')
    #     return HttpResponse(f"Kite login failed or was denied. Status: {status}")