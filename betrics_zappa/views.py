from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from requests import post as AWS_POST

@csrf_exempt
def user_login(request):
    if request.method == "POST":
        url = "https://aws.betrics.io/user/login"

        headers = {
            'Content-Type': 'application/json'
        }
        response = AWS_POST(url, headers=headers, data=request.body)
        return JsonResponse(response.json(), safe=False)
    else:
        return JsonResponse({"body": "GET method is not allowed"})
