from django.contrib import admin
from .models import Candle


class CandleAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'open_price', 'high_price', 'low_price', 'close_price', 'volume_delta']
    search_fields = ['created_at', 'open_price', 'high_price']
    list_filter = ['created_at']


admin.site.register(Candle, CandleAdmin)
