from django.db import models


class O11yLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.CharField(max_length=500)
    method = models.CharField(max_length=20)
    session_id = models.CharField(max_length=50, null=True, blank=True)

    request_start = models.DateTimeField(null=True, blank=True)
    request_end = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)

    request_payload = models.JSONField(null=True, blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)

    exception = models.TextField(null=True, blank=True)
    logs = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f'O11y Log: {self.url} - {self.method} @ {self.created_at.isoformat()}'
