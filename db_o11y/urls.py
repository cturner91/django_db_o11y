from django.urls import path

from .views import JsonViews, HtmlViews, ErrorViews, MiscViews


urlpatterns = [
    path('html/', HtmlViews.as_view(), name='html'),
    path('json/', JsonViews.as_view(), name='json'),
    path('error/', ErrorViews.as_view(), name='error'),
    path('misc/', MiscViews.as_view(), name='misc'),
]
