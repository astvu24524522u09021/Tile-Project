from django.shortcuts import render

from accounts.permissions import admin_required
from .services import (
    get_godown_report,
    get_inventory_overview,
    get_low_stock_report,
    get_prediction_report,
    get_transaction_report,
    get_transfer_report,
)


@admin_required
def inventory_report_view(request):
    data = get_inventory_overview()
    return render(request, 'reports/inventory_report.html', {'data': data})


@admin_required
def godown_report_view(request):
    data = get_godown_report()
    return render(request, 'reports/godown_report.html', {'data': data})


@admin_required
def low_stock_report_view(request):
    data = get_low_stock_report()
    return render(request, 'reports/low_stock_report.html', {'data': data})


@admin_required
def transaction_report_view(request):
    data = get_transaction_report()
    return render(request, 'reports/transaction_report.html', {'data': data})


@admin_required
def transfer_report_view(request):
    data = get_transfer_report()
    return render(request, 'reports/stock_transfer_report.html', {'data': data})


@admin_required
def ml_report_view(request):
    data = get_prediction_report()
    return render(request, 'reports/ml_prediction_report.html', {'data': data})
