from django.urls import path

from .views import (
    JsonViews, HtmlViews, ErrorViews, MiscViews, HtmlFunView, Handled404View, Unhandled404View
)


urlpatterns = [
    path('html/', HtmlViews.as_view(), name='html'),
    path('json/', JsonViews.as_view(), name='json'),
    path('error/', ErrorViews.as_view(), name='error'),
    path('misc/', MiscViews.as_view(), name='misc'),
    path('html-fun/', HtmlFunView, name='html-fun'),
    path('error-fun/', HtmlFunView, name='error-fun'),
    path('h404/', Handled404View, name='h404'),
    path('u404/', Unhandled404View, name='u404'),
]
