from betrics_manager.betrics.user import model
from django.http import HttpResponse


class JwtTokenAuthenticationMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response
        self.ignore_function_list = ["user_login"]
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        if view_func.__name__ in self.ignore_function_list:
            return None
        else:
            try:
                user = model.authenticate_user(request.headers)
                setattr(request, 'user', user)
                return None
            except Exception as error:
                return HttpResponse("Token is Not valid or Expired")
