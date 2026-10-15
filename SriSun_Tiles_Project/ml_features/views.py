from django.shortcuts import render

from accounts.permissions import admin_required
from .services import get_model_status, get_prediction_summary


@admin_required
def prediction_view(request):
    summary = get_model_status()
    return render(request, 'ml/prediction.html', {'summary': summary})


@admin_required
def prediction_result_view(request):
    summary = get_prediction_summary()
    return render(request, 'ml/prediction_result.html', {'summary': summary})
