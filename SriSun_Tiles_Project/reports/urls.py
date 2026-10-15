from django.urls import path

from . import views

urlpatterns = [
    path('inventory/', views.inventory_report_view, name='inventory_report'),
    path('godown/', views.godown_report_view, name='godown_report'),
    path('low-stock/', views.low_stock_report_view, name='low_stock_report'),
    path('transactions/', views.transaction_report_view, name='transaction_report'),
    path('transfers/', views.transfer_report_view, name='transfer_report'),
    path('ml/', views.ml_report_view, name='ml_report'),
]
