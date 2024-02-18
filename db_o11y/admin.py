from django.contrib import admin

from .models import O11yLog


class O11yLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'url', 'method', 'response_code']
    list_filter = ['created_at', 'url', 'method', 'response_code']


admin.site.register(O11yLog, O11yLogAdmin)
