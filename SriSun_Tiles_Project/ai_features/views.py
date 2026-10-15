from django.contrib import messages
from django.shortcuts import render

from .services import search_tiles_for_ai_query


def assistant_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    summary = {'message': 'Use the assistant to search tile inventory.'}

    if query:
        summary = search_tiles_for_ai_query(query)
        results = summary.get('results', [])
        if not results:
            messages.info(request, summary.get('message', 'No results found.'))

    return render(request, 'ai/assistant.html', {'query': query, 'results': results, 'summary': summary})
