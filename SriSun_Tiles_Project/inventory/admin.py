from django.contrib import admin

from .models import Godown, InventoryStock, StockTransaction, StockTransfer


@admin.register(Godown)
class GodownAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location')
    search_fields = ('name', 'code')


@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = ('tile', 'godown', 'quantity', 'last_updated')
    list_filter = ('godown',)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('tile', 'godown', 'transaction_type', 'quantity', 'created_at')
    list_filter = ('transaction_type', 'godown')


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('tile', 'source_godown', 'destination_godown', 'quantity', 'created_at')
    list_filter = ('source_godown', 'destination_godown')
