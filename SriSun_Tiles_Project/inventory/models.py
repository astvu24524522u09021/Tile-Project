from django.conf import settings
from django.db import models

from tiles.models import Tile


class Godown(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class InventoryStock(models.Model):
    tile = models.ForeignKey(Tile, on_delete=models.CASCADE, related_name='stock_entries')
    godown = models.ForeignKey(Godown, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tile', 'godown')

    def __str__(self):
        return f"{self.tile.model_id} - {self.godown.name}: {self.quantity}"


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('ADD', 'Add Stock'),
        ('REMOVE', 'Remove Stock'),
        ('TRANSFER_IN', 'Transfer In'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    tile = models.ForeignKey(Tile, on_delete=models.CASCADE, related_name='transactions')
    godown = models.ForeignKey(Godown, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tile.model_id} {self.transaction_type} {self.quantity} @ {self.godown.name}"


class StockTransfer(models.Model):
    tile = models.ForeignKey(Tile, on_delete=models.CASCADE, related_name='transfers')
    source_godown = models.ForeignKey(Godown, on_delete=models.CASCADE, related_name='outgoing_transfers')
    destination_godown = models.ForeignKey(Godown, on_delete=models.CASCADE, related_name='incoming_transfers')
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=30, default='completed')
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transfer {self.tile.model_id}: {self.source_godown} -> {self.destination_godown}"
