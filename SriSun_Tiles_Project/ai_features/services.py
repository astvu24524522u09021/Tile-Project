import re

from django.db.models import Q, Sum

from inventory.models import InventoryStock
from tiles.models import Tile


def _normalize_query(query):
    return query.strip().lower()


def parse_query_terms(query):
    q = _normalize_query(query)
    filters = {}
    if not q:
        return filters

    tokens = re.findall(r"[a-zA-Z0-9xX]+", q)
    if not tokens:
        return filters

    for token in tokens:
        token_lower = token.lower()
        if token_lower in {'white', 'beige', 'black', 'grey', 'gray', 'brown', 'red', 'blue', 'green', 'ivory'}:
            filters['color__icontains'] = token_lower
        elif token_lower in {'bathroom', 'kitchen', 'living', 'hall', 'floor'}:
            filters['category__icontains'] = token_lower
        elif token_lower in {'matte', 'glossy', 'polished', 'wood', 'marble'}:
            filters['finish__icontains'] = token_lower
        elif 'x' in token_lower:
            filters['size__icontains'] = token_lower.replace('x', 'x')
        elif token_lower in {'low', 'stock'}:
            continue
    return filters


def search_tiles_for_ai_query(query):
    q = _normalize_query(query)
    if not q:
        return {'message': 'Please enter a tile search query.', 'results': []}

    tiles = Tile.objects.all()
    filters = parse_query_terms(q)

    if 'low' in q and 'stock' in q:
        low_stock_tiles = []
        for tile in tiles:
            total_stock = InventoryStock.objects.filter(tile=tile).aggregate(total=Sum('quantity'))['total'] or 0
            if total_stock < 20:
                low_stock_tiles.append(tile)
        return {
            'message': 'Here are the low-stock tiles matching your request.',
            'results': low_stock_tiles,
        }

    if filters:
        qset = tiles.filter(**filters)
    else:
        qset = tiles.filter(
            Q(name__icontains=q)
            | Q(model_id__icontains=q)
            | Q(category__icontains=q)
            | Q(size__icontains=q)
            | Q(color__icontains=q)
            | Q(finish__icontains=q)
            | Q(description__icontains=q)
        )

    if not qset.exists():
        return {
            'message': 'No matching tiles were found. Try searching by model ID, colour, size, category, or finish.',
            'results': [],
        }

    return {
        'message': f"Found {qset.count()} tile(s) for your request.",
        'results': list(qset)
    }
