from django.db.models import Sum

from inventory.models import Godown, InventoryStock, StockTransaction, StockTransfer
from tiles.models import Tile


def get_inventory_overview():
    entries = InventoryStock.objects.select_related('tile', 'godown').order_by('tile__model_id')
    total_stock = sum(item.quantity for item in entries)
    return {
        'entries': entries,
        'total_stock': total_stock,
        'tile_count': Tile.objects.count(),
    }


def get_godown_report():
    godowns = []
    for godown in Godown.objects.all():
        quantity = InventoryStock.objects.filter(godown=godown).aggregate(total=Sum('quantity'))['total'] or 0
        godowns.append({'godown': godown, 'total_quantity': quantity})
    return godowns


def get_low_stock_report():
    entries = InventoryStock.objects.select_related('tile', 'godown').filter(quantity__lt=20).order_by('quantity')
    return entries


def get_transaction_report():
    return StockTransaction.objects.select_related('tile', 'godown').order_by('-created_at')


def get_transfer_report():
    return StockTransfer.objects.select_related('tile', 'source_godown', 'destination_godown').order_by('-created_at')


def get_prediction_report():
    from ml_features.services import get_prediction_summary

    return get_prediction_summary()
