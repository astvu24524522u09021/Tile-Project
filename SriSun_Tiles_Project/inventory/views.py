from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect, render

from tiles.models import Tile

from accounts.permissions import admin_required
from .forms import AddStockForm, RemoveStockForm, TransferStockForm
from .models import Godown, InventoryStock, StockTransaction, StockTransfer


@admin_required
def dashboard_view(request):
    tiles = Tile.objects.all()
    stock_entries = InventoryStock.objects.select_related('tile', 'godown')
    total_stock = stock_entries.aggregate(total=Sum('quantity'))['total'] or 0

    godown_totals = []
    for godown in Godown.objects.all():
        qty = stock_entries.filter(godown=godown).aggregate(total=Sum('quantity'))['total'] or 0
        godown_totals.append({'godown': godown, 'quantity': qty})

    low_stock = stock_entries.filter(quantity__lt=20).order_by('quantity')[:10]
    recent_transactions = StockTransaction.objects.select_related('tile', 'godown').order_by('-created_at')[:8]
    recent_transfers = StockTransfer.objects.select_related('tile', 'source_godown', 'destination_godown').order_by('-created_at')[:6]

    return render(
        request,
        'inventory/dashboard.html',
        {
            'total_tiles': tiles.count(),
            'total_stock': total_stock,
            'godown_totals': godown_totals,
            'low_stock': low_stock,
            'recent_transactions': recent_transactions,
            'recent_transfers': recent_transfers,
        },
    )


@admin_required
def stock_view(request):
    stock_entries = InventoryStock.objects.select_related('tile', 'godown').order_by('tile__model_id')
    return render(request, 'inventory/stock.html', {'stock_entries': stock_entries})


@admin_required
def add_stock_view(request):
    if request.method == 'POST':
        form = AddStockForm(request.POST)
        if form.is_valid():
            tile = form.cleaned_data['tile']
            godown = Godown.objects.get(id=form.cleaned_data['godown'])
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            stock, _ = InventoryStock.objects.get_or_create(tile=tile, godown=godown)
            stock.quantity += quantity
            stock.save()
            StockTransaction.objects.create(
                tile=tile,
                godown=godown,
                quantity=quantity,
                transaction_type='ADD',
                notes=notes,
                created_by=request.user,
            )
            messages.success(request, f'Added {quantity} units of {tile.model_id} to {godown.name}.')
            return redirect('stock_view')
    else:
        form = AddStockForm()
    return render(request, 'inventory/add_stock.html', {'form': form})


@admin_required
def remove_stock_view(request):
    if request.method == 'POST':
        form = RemoveStockForm(request.POST)
        if form.is_valid():
            tile = form.cleaned_data['tile']
            godown = Godown.objects.get(id=form.cleaned_data['godown'])
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            stock = InventoryStock.objects.filter(tile=tile, godown=godown).first()
            if not stock or stock.quantity < quantity:
                messages.error(request, 'Requested removal quantity exceeds current stock.')
                return render(request, 'inventory/remove_stock.html', {'form': form})
            stock.quantity -= quantity
            stock.save()
            StockTransaction.objects.create(
                tile=tile,
                godown=godown,
                quantity=quantity,
                transaction_type='REMOVE',
                notes=notes,
                created_by=request.user,
            )
            messages.success(request, f'Removed {quantity} units of {tile.model_id} from {godown.name}.')
            return redirect('stock_view')
    else:
        form = RemoveStockForm()
    return render(request, 'inventory/remove_stock.html', {'form': form})


@admin_required
def transfer_stock_view(request):
    if request.method == 'POST':
        form = TransferStockForm(request.POST)
        if form.is_valid():
            tile = form.cleaned_data['tile']
            source = Godown.objects.get(id=form.cleaned_data['source_godown'])
            destination = Godown.objects.get(id=form.cleaned_data['destination_godown'])
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']

            if source.id == destination.id:
                messages.error(request, 'Source and destination godowns must be different.')
                return render(request, 'inventory/transfer_stock.html', {'form': form})

            try:
                with transaction.atomic():
                    source_stock = InventoryStock.objects.select_for_update().filter(tile=tile, godown=source).first()
                    if not source_stock or source_stock.quantity < quantity:
                        raise ValueError('Insufficient stock in source godown.')

                    source_stock.quantity -= quantity
                    source_stock.save()

                    dest_stock, _ = InventoryStock.objects.get_or_create(tile=tile, godown=destination)
                    dest_stock.quantity += quantity
                    dest_stock.save()

                    StockTransaction.objects.create(
                        tile=tile,
                        godown=source,
                        quantity=quantity,
                        transaction_type='TRANSFER_OUT',
                        notes=f'Transferred to {destination.name}. {notes}',
                        created_by=request.user,
                    )
                    StockTransaction.objects.create(
                        tile=tile,
                        godown=destination,
                        quantity=quantity,
                        transaction_type='TRANSFER_IN',
                        notes=f'Received from {source.name}. {notes}',
                        created_by=request.user,
                    )

                    StockTransfer.objects.create(
                        tile=tile,
                        source_godown=source,
                        destination_godown=destination,
                        quantity=quantity,
                        notes=notes,
                        created_by=request.user,
                    )
            except ValueError as exc:
                messages.error(request, str(exc))
                return render(request, 'inventory/transfer_stock.html', {'form': form})

            messages.success(request, f'Transferred {quantity} units of {tile.model_id} from {source.name} to {destination.name}.')
            return redirect('stock_view')
    else:
        form = TransferStockForm()
    return render(request, 'inventory/transfer_stock.html', {'form': form})


@admin_required
def transactions_view(request):
    transactions = StockTransaction.objects.select_related('tile', 'godown').order_by('-created_at')
    return render(request, 'inventory/transactions.html', {'transactions': transactions})
