import json
from random import random
from unittest.mock import MagicMock

from django.http import HttpResponse, JsonResponse
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.urls import reverse

from .models import O11yLog
from .views import HtmlViews, HtmlFunView, ErrorFunView
from .utils import (
    auto_log, 
    _extract_base_url, 
    _extract_request, 
    _extract_request_payload, 
    _extract_response_payload,
    _extract_session_id, 
    _get_500,
)


def _pre_configure_response(func, request):
    '''Simple utility method to generate the expected response and remove the associated log

    Had REAL difficulty in finding a testing solution that would let me configure custom inputs
    for the decorator.
    We CANNOT instantiate view method inside decorated dummy function - otherwise, the default 
    decorator values are applied. Instead, pre-compute the result and return it. This way, the 
    decorator is called with defaults BEFORE it is called with the specified values.

    Also need to keep the one input argument on the dummy function for *args parsing.

    This also means that two logs are created for each request which isn't ideal, so we clean up 
    in here too.

    Maybe it would have been easier to configure 4 different views -> FF, TF, FT, TT. But that
    approach is not extendable if the decorator gets extra inputs in future.
    '''
    response = func(request)
    O11yLog.objects.last().delete()
    return response


class WithClientMixin(TestCase):
    def setUp(self, *args, **kwargs):
        self.client = Client()
        super().setUp(*args, **kwargs)


class AutoLogTest(WithClientMixin):

    def test_get_with_defaults(self):
        self.assertEqual(O11yLog.objects.count(), 0)
        self.client.get(reverse('html'))
        self.assertEqual(O11yLog.objects.count(), 1)

        log = O11yLog.objects.first()
        self.assertEqual(log.response_code, 200)
        self.assertIsNone(log.request_payload)
        self.assertIsNone(log.response_payload)
        self.assertIsNone(log.exception)
        self.assertEqual(len(log.logs), 1)

    def test_get_with_custom_config(self):
        request = RequestFactory().get(f'{reverse("html")}?key1=value1')

        for log_inputs, log_outputs in (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ):
            with self.subTest(f'{log_inputs}, {log_outputs}'):
                pre = _pre_configure_response(HtmlViews().get, request) 
                @auto_log(log_inputs, log_outputs)
                def view(request):
                    return pre
                view(request)

                log = O11yLog.objects.last()
                if log_inputs:
                    self.assertDictEqual(log.request_payload, {'key1': 'value1'})
                else:
                    self.assertIsNone(log.request_payload)

                if log_outputs:
                    self.assertEqual(log.response_payload, '<h1>GET</h1>')
                else:
                    self.assertIsNone(log.response_payload)

    def test_different_methods(self):
        for method, method_name in (
            (self.client.get, 'GET'),
            (self.client.post, 'POST'),
            (self.client.put, 'PUT'),
            (self.client.patch, 'PATCH'),
            (self.client.delete, 'DELETE'),
        ):
            with self.subTest(f'{method_name=}'):
                method(reverse('json'))
                log = O11yLog.objects.last()
                self.assertEqual(log.method, method_name)

    def test_with_exception_no_catch(self):
        # POST endpoint has catch_exceptions=False
        with self.assertRaises(Exception):
            self.client.post(reverse('error'))

        log = O11yLog.objects.last()
        self.assertIsNotNone(log.exception)
        self.assertIn('POST', log.exception)

    def test_with_exception_with_catch(self):
        # GET endpoint has catch_exceptions=True
        self.client.get(reverse('error'))

        log = O11yLog.objects.last()
        self.assertIsNotNone(log.exception)
        self.assertIn('GET', log.exception)

    def test_with_multiple_logs(self):
        # misc GET view has a 1s sleep and two logs
        self.client.get(reverse('misc'))

        log = O11yLog.objects.last()
        self.assertGreater(log.duration, 1)
        self.assertEqual(len(log.logs), 2)
        for item in log.logs:
            self.assertIn('message', item)
            self.assertIn('elapsed', item)


class ExtractRequestBaseUrlTest(WithClientMixin):
    
    def test_basic_url(self):
        url = reverse("html")
        request = RequestFactory().get(url)
        extracted = _extract_base_url(request)
        self.assertEqual(extracted, url)

    def test_url_with_query_params(self):
        url = reverse("html")
        request = RequestFactory().get(f'{url}?key1=value1')
        extracted = _extract_base_url(request)
        self.assertEqual(extracted, url)


class ExtractRequestTest(WithClientMixin):

    def test_first_arg(self):
        request = RequestFactory().get(reverse("html"))
        self.assertEqual(_extract_request(request), request)

    def test_second_arg(self):
        request = RequestFactory().get(reverse("html"))
        self.assertEqual(_extract_request(None, request), request)

    def test_random_arg(self):
        request = RequestFactory().get(reverse("html"))

        args = [i for i in range(100)]
        idx = int(random()*100)
        args[idx] = request
        self.assertEqual(_extract_request(*args), request)

    def test_no_request_present(self):
        args = [i for i in range(100)]
        with self.assertRaises(Exception):
            _extract_request(*args)


class ExtractRequestPayloadTest(WithClientMixin):
    
    def test_get_no_query_params(self):
        request = RequestFactory().get(reverse("html"))
        payload = _extract_request_payload(request)
        self.assertIsNone(payload)

    def test_get_with_query_params(self):
        request = RequestFactory().get(f'{reverse("html")}?key1=value1')
        payload = _extract_request_payload(request)
        self.assertDictEqual(payload, {'key1': 'value1'})

    def test_post(self):
        request = RequestFactory().post(reverse("html"), data={'key': 'value', 'key2': 'value2'})
        payload = _extract_request_payload(request)
        self.assertDictEqual(payload, {'key': 'value', 'key2': 'value2'})

    def test_put(self):
        request = RequestFactory().put(reverse("html"), data=json.dumps({'key': 'value', 'key2': 'value2'}))
        payload = _extract_request_payload(request)
        self.assertDictEqual(payload, {'key': 'value', 'key2': 'value2'})

    def test_delete(self):
        request = RequestFactory().delete(reverse("html"), data=json.dumps({'key': 'value', 'key2': 'value2'}))
        payload = _extract_request_payload(request)
        self.assertDictEqual(payload, {'key': 'value', 'key2': 'value2'})


class ExtractResponsePayloadTest(WithClientMixin):
    
    def test_response_html(self):
        response = HttpResponse('<h1>GET</h1>')
        payload = _extract_response_payload(response)
        self.assertEqual(payload, '<h1>GET</h1>')

    def test_response_json(self):
        response = JsonResponse({'key': 'value'})
        payload = _extract_response_payload(response)
        self.assertDictEqual(payload, {'key': 'value'})


class ExtractSessionTest(WithClientMixin):

    def test_no_session(self):
        request = RequestFactory().get(reverse("html"))
        self.assertIsNone(_extract_session_id(request))
    
    def test_with_session_but_no_key(self):
        request = RequestFactory().get(reverse("html"))
        request.session = {}
        self.assertIsNone(_extract_session_id(request))

    def test_with_session_and_key(self):
        request = RequestFactory().get(reverse("html"))
        request.session = MagicMock()
        request.session.session_key = '123'
        self.assertEqual(_extract_session_id(request), '123')


class Get500Test(WithClientMixin):

    def test_with_html_request(self):
        from db_o11y.utils import HTML_500
        request = RequestFactory().get(reverse("error"))
        result = _get_500(request, None)
        self.assertEqual(result, HTML_500)

    def test_with_json_request(self):
        from db_o11y.utils import JSON_500
        request = RequestFactory().get(reverse("error"), headers={'Content-Type': 'application/json'})
        result = _get_500(request, None)
        self.assertEqual(result, JSON_500)

    def test_with_custom_500(self):
        custom_500 = JsonResponse({'new_key': 'new_value'}, status=500)
        request = RequestFactory().get(reverse("error"))
        result = _get_500(request, custom_500)
        self.assertEqual(result, custom_500)


class FunctionViewTest(WithClientMixin):

    def test_get_with_custom_config(self):
        request = RequestFactory().get(f'{reverse("html-fun")}?key1=value1')

        for log_inputs, log_outputs in (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ):
            with self.subTest(f'{log_inputs}, {log_outputs}'):
                pre = _pre_configure_response(HtmlFunView, request) 
                @auto_log(log_inputs, log_outputs)
                def view(request):
                    return pre
                view(request)

                log = O11yLog.objects.last()
                if log_inputs:
                    self.assertDictEqual(log.request_payload, {'key1': 'value1'})
                else:
                    self.assertIsNone(log.request_payload)

                if log_outputs:
                    self.assertEqual(log.response_payload, '<h1>GET via function</h1>')
                else:
                    self.assertIsNone(log.response_payload)
    
    def test_add_logs(self):
        request = RequestFactory().get(f'{reverse("html-fun")}?key1=value1')
        HtmlFunView(request)

        log = O11yLog.objects.last()
        self.assertEqual(len(log.logs), 2)
        for item in log.logs:
            self.assertIn('message', item)
            self.assertIn('elapsed', item)
    
    def test_error_handled(self):
        request = RequestFactory().get(reverse("error-fun"))

        @auto_log(catch_exceptions=True)
        def view(request):
            return ErrorFunView(request)
        view(request)

        log = O11yLog.objects.last()
        self.assertIsNotNone(log.exception)

    def test_error_unhandled(self):
        request = RequestFactory().get(reverse("error-fun"))

        @auto_log(catch_exceptions=False)
        def view(request):
            return ErrorFunView(request)
        
        with self.assertRaises(ValueError):
            view(request)

        log = O11yLog.objects.last()
        self.assertIsNotNone(log.exception)

    def test_error_custom_500(self):
        request = RequestFactory().get(reverse("error-fun"))
        custom_500 = JsonResponse({'message': 'error'}, status=500)

        @auto_log(catch_exceptions=True, http500=custom_500)
        def view(request):
            return ErrorFunView(request)
        response = view(request)

        self.assertEqual(response, custom_500)
