# middleware.py
import json
from django.http import JsonResponse

class JSONErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(exception)
            }, status=500)
        return None
    

