import base64
from io import BytesIO

from django.contrib import messages
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from PIL import Image, ImageOps

from inventory.models import InventoryStock
from accounts.permissions import admin_required

from .forms import TileForm, TileScanForm
from .image_matching import find_exact_sample_match
from .models import Tile


def tile_list_view(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    color = request.GET.get('color', '').strip()
    finish = request.GET.get('finish', '').strip()
    tiles = Tile.objects.annotate(
        total_stock=Coalesce(Sum('stock_entries__quantity'), Value(0)),
    )

    if query:
        search_fields = ('model_id', 'name', 'category', 'size', 'color', 'finish', 'description')
        for term in query.split():
            term_filter = Q()
            for field in search_fields:
                term_filter |= Q(**{f'{field}__icontains': term})
            tiles = tiles.filter(term_filter)
    if category:
        tiles = tiles.filter(category=category)
    if color:
        tiles = tiles.filter(color=color)
    if finish:
        tiles = tiles.filter(finish=finish)

    tile_data = [
        {
            'tile': tile,
            'total_stock': tile.total_stock,
        }
        for tile in tiles
    ]

    filters = {
        'categories': Tile.objects.order_by('category').values_list('category', flat=True).distinct(),
        'colors': Tile.objects.order_by('color').values_list('color', flat=True).distinct(),
        'finishes': Tile.objects.order_by('finish').values_list('finish', flat=True).distinct(),
        'category': category,
        'color': color,
        'finish': finish,
    }
    return render(request, 'tiles/tile_list.html', {'tiles': tile_data, 'query': query, **filters})


@admin_required
def tile_admin_list_view(request):
    tiles = Tile.objects.annotate(
        total_stock=Coalesce(Sum('stock_entries__quantity'), Value(0)),
    ).order_by('model_id')
    return render(request, 'tiles/admin_product_list.html', {'tiles': tiles})


def tile_scan_view(request):
    form = TileScanForm(request.POST or None, request.FILES or None)
    context = {'form': form}

    if request.method == 'POST' and form.is_valid():
        uploaded_image = form.cleaned_data['image']
        image_data = uploaded_image.read()
        uploaded_image.seek(0)

        with Image.open(BytesIO(image_data)) as image:
            preview = ImageOps.exif_transpose(image).convert('RGB')
            preview.thumbnail((1280, 960), Image.Resampling.LANCZOS)
            preview_buffer = BytesIO()
            preview.save(preview_buffer, format='JPEG', quality=88, optimize=True)
        context['preview_data'] = base64.b64encode(preview_buffer.getvalue()).decode('ascii')

        tile = find_exact_sample_match(image_data)
        if tile is None:
            context['no_match'] = True
        else:
            context['tile'] = tile
            context['total_stock'] = InventoryStock.objects.filter(tile=tile).aggregate(
                total=Coalesce(Sum('quantity'), Value(0)),
            )['total']

    return render(request, 'tiles/tile_scan.html', context)


def tile_detail_view(request, pk):
    tile = get_object_or_404(Tile, pk=pk)
    stock_entries = InventoryStock.objects.filter(tile=tile).select_related('godown')
    total_stock = stock_entries.aggregate(total=Sum('quantity'))['total'] or 0
    return render(request, 'tiles/tile_detail.html', {'tile': tile, 'stock_entries': stock_entries, 'total_stock': total_stock})


@admin_required
def tile_create_view(request):
    if request.method == 'POST':
        form = TileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tile model created successfully.')
            return redirect('admin_product_list')
    else:
        form = TileForm()
    return render(request, 'tiles/tile_form.html', {'form': form, 'title': 'Add Tile'})


@admin_required
def tile_update_view(request, pk):
    tile = get_object_or_404(Tile, pk=pk)
    if request.method == 'POST':
        form = TileForm(request.POST, request.FILES, instance=tile)
        form.fields['model_id'].disabled = True
        if form.is_valid():
            form.save()
            messages.success(request, 'Tile model updated successfully.')
            return redirect('admin_product_list')
    else:
        form = TileForm(instance=tile)
        form.fields['model_id'].disabled = True
    return render(request, 'tiles/tile_form.html', {'form': form, 'title': 'Update Tile'})


@admin_required
def tile_delete_view(request, pk):
    tile = get_object_or_404(Tile, pk=pk)
    if request.method == 'POST':
        tile.delete()
        messages.success(request, 'Tile model deleted successfully.')
        return redirect('admin_product_list')
    return render(request, 'tiles/tile_confirm_delete.html', {'tile': tile})
