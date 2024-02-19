from datetime import datetime
from time import sleep

from django.http import HttpResponse, JsonResponse
from django.views import View

from .utils import auto_log


class HtmlViews(View):

    @auto_log()
    def get(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return HttpResponse('<h1>GET</h1>', status=200)

    @auto_log()
    def post(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return HttpResponse('<h1>POST</h1>', status=201)

    @auto_log()
    def put(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return HttpResponse('<h1>PUT</h1>', status=200)


class JsonViews(View):

    @auto_log()
    def get(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return JsonResponse({'message': 'GET'}, status=200)

    @auto_log()
    def post(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return JsonResponse({'message': 'POST'}, status=201)

    @auto_log()
    def put(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return JsonResponse({'message': 'PUT'}, status=200)

    @auto_log()
    def patch(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return JsonResponse({'message': 'PATCH'}, status=200)

    @auto_log()
    def delete(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        return JsonResponse({'message': 'DELETE'}, status=200)


class ErrorViews(View):

    @auto_log()
    def get(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        raise Exception('Raising on GET')

    @auto_log(catch_exceptions=False)
    def post(self, request, *args, **kwargs):
        request.add_log(f'NOW = {datetime.utcnow().isoformat()}')
        raise Exception('Raising on POST')


class MiscViews(View):

    @auto_log()
    def get(self, request, *args, **kwargs):
        '''Multiple logs, including a delay'''
        dt1 = datetime.utcnow()
        request.add_log(f'Request started: {dt1.isoformat()}')

        sleep(1)

        dt2 = datetime.utcnow()
        request.add_log(f'Request ended: = {dt2.isoformat()}')

        return JsonResponse({
            'message': 'GET', 
            'time': (dt2-dt1).total_seconds()
        }, status=200)


@auto_log()
def HtmlFunView(request):
    request.add_log(f'Start at: {datetime.utcnow().isoformat()}')
    sleep(0.2)
    request.add_log(f'End at: {datetime.utcnow().isoformat()}')
    return HttpResponse('<h1>GET via function</h1>', status=200)


# Note: no decorator. The decorator is added in the tests.
def ErrorFunView(request):
    request.add_log(f'Start at: {datetime.utcnow().isoformat()}')
    raise ValueError('Bad value')
