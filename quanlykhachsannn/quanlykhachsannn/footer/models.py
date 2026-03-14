from django.db import models

class FooterText(models.Model):
    text = models.CharField(max_length=200, )
    is_editable = models.BooleanField(default=False, help_text="Only superusers can edit if unchecked")

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Footer Text"
        verbose_name_plural = "Footer Text"