from django.db import models

class UpbitData(models.Model):
    market = models.CharField(max_length=10)
    date_time = models.DateTimeField(db_index=True)
    opening_price = models.FloatField(null=True)
    high_price = models.FloatField(null=True)
    low_price = models.FloatField(null=True)
    closing_price = models.FloatField(null=True)
    acc_price = models.FloatField(null=True)
    acc_volume = models.FloatField(null=True)

    class Meta:
        unique_together = ('market', 'date_time')
        ordering = ['date_time']
        app_label = 'data_provider'
    
    def __str__(self):
        return f"{self.market} at {self.date_time}"
