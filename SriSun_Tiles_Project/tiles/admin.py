from django.contrib import admin

from .models import Tile


@admin.register(Tile)
class TileAdmin(admin.ModelAdmin):
    list_display = ('model_id', 'name', 'category', 'size', 'color', 'price')
    search_fields = ('model_id', 'name', 'category')
    list_filter = ('category', 'color', 'finish')
