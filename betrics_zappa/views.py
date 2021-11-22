from django.views.decorators.csrf import csrf_exempt
import json
from lambda_functions.user_auth import login
from django.http import JsonResponse, HttpResponse

@csrf_exempt
def user_login(request):
    if request.method == "POST":

        body = request.body
        data = json.loads(body.decode("utf-8"))

        response = login.lambda_handler(data)
        return HttpResponse("happy")
    else:
        return JsonResponse({"body": "GET method is not allowed"})
