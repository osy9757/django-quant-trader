from django.db import models

class UpbitData(models.Model):
    period = models.IntegerField()
    recovered = models.BooleanField(default=False)
    market = models.CharField(max_length=10)
    date_time = models.DateTimeField()
    opening_price = models.FloatField()
    high_price = models.FloatField()
    low_price = models.FloatField()
    closing_price = models.FloatField()
    acc_price = models.FloatField()
    acc_volume = models.FloatField()

    class Meta:
        unique_together = ('period', 'market', 'date_time')
        ordering = ['date_time']
    
    def __str__(self):
        return f"{self.market} at {self.date_time}"
