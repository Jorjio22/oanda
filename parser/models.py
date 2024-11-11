from django.db import models


class Candle(models.Model):
    open_price = models.DecimalField(max_digits=20, decimal_places=10)
    high_price = models.DecimalField(max_digits=20, decimal_places=10)
    low_price = models.DecimalField(max_digits=20, decimal_places=10)
    average_value = models.DecimalField(max_digits=20, decimal_places=10)
    absolute_volatility = models.DecimalField(max_digits=20, decimal_places=10)
    percentage_volatility_open = models.DecimalField(max_digits=20, decimal_places=10)
    percentage_volatility_low = models.DecimalField(max_digits=20, decimal_places=10)
    close_price = models.DecimalField(max_digits=20, decimal_places=10)
    number_of_changes = models.IntegerField()
    max_delay = models.DecimalField(max_digits=20, decimal_places=10)
    min_delay = models.DecimalField(max_digits=20, decimal_places=10)
    average_delay = models.DecimalField(max_digits=20, decimal_places=10)
    volume_start = models.DecimalField(max_digits=20, decimal_places=10)
    volume_stop = models.DecimalField(max_digits=20, decimal_places=10)
    volume_delta = models.DecimalField(max_digits=20, decimal_places=10)
    volume_percent_change = models.DecimalField(max_digits=20, decimal_places=10)
    volume_average_per_minute = models.DecimalField(max_digits=20, decimal_places=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Candle at {self.created_at} - Open: {self.open_price}, Close: {self.close_price}"
