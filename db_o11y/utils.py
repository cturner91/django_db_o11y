from functools import wraps
import json
import traceback

from django.http import HttpResponse, JsonResponse
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone

from .models import O11yLog


HTML_500 = HttpResponse('<h1>Unexpected error</h1>', status=500)
JSON_500 = JsonResponse({"message": "Unexpected error"}, status=500)


def auto_log(log_inputs=False, log_outputs=False, catch_exceptions=True, http500=None):
    '''Decorator that allows capturing logs during a request
    
    Recognise that users can share sensitive data in requests e.g. passwords. 
    Therefore logging of inputs and outputs is disabled by default.

    If catch_exceptions is enabled then if the code raises an exception, it is caught, the 
    exception is captured, and the user gets a generic Http500 response.

    The decorator configures a method on the request object called 'add_log'. This appends to
    a list on the decorator namespace, and within the Django view code, individual logs can be 
    appended. Then, when the view is finished and the response has been generated, these logs 
    are committed to the DB.
    '''
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            request = _extract_request(*args)
            logs = []
            dt0 = timezone.now()

            # this variable can be customised if necessary
            setattr(request, 'add_log', lambda message: logs.append({
                'elapsed': (timezone.now() - dt0).total_seconds(),
                'message': message,
            }))
            log = O11yLog(
                url=_extract_base_url(request), 
                method=request.method,
                session_id=_extract_session_id(request),
                request_payload=_extract_request_payload(request) if log_inputs else None,
                request_start=timezone.now(),
            )

            # need to track whether code has raised exception or not and alter behaviour accordingly
            exc = None
            try:
                response = func(*args, **kwargs)
            except Exception as e:
                log.exception = traceback.format_exc()
                exc = e
            finally:
                if exc and catch_exceptions:
                    response = _get_500(request, http500)
                    exc = None

                # block cannot be run if there is an exception and it should be raised
                if not exc:
                    log.response_code = response.status_code
                    log.response_payload = (
                        _extract_response_payload(response) if log_outputs else None
                    )

                log.logs = logs
                log.request_end = timezone.now()
                log.duration = (log.request_end - log.request_start).total_seconds()
                log.save()

                if exc and not catch_exceptions:
                    raise exc

            return response
        return inner
    return outer


def _extract_base_url(request):
    return request.path.split('?')[0]


def _extract_request_payload(request):
    '''Simple function to get payload from request into easily readable / seriailizable format'''
    if request.method == 'GET':
        return {key: request.GET[key] for key in request.GET} or None
    elif request.method == 'POST':
        return {key: request.POST[key] for key in request.POST} or None
    else:
        return json.loads(request.body.decode('utf-8')) or None


def _extract_session_id(request):
    if hasattr(request, 'session') and hasattr(request.session, 'session_key'):
        return request.session.session_key
    return None


def _extract_response_payload(response):
    if isinstance(response, JsonResponse):
        return json.loads(response.content) or None
    if isinstance(response.content, bytes):
        return response.content.decode('utf-8') or None
    return str(response.content) or None


def _extract_request(*args):
    '''This allows decorator to be run as function (args[0]) or class-based view (args[1])'''
    for arg in args:
        if isinstance(arg, WSGIRequest):
            return arg
    raise TypeError('None of the inputs were subclasses of WSGIRequest')


def _get_500(request, http500):
    '''Utility returns a JSON object if the request is JSON, otherwise returns HTML
    If user provides their own http500 object, then that is used'''
    if http500 is not None:
        return http500
    else:
        if request.content_type == 'application/json':
            return JSON_500
        else:
            return HTML_500
