from django.urls import path

from . import views

urlpatterns = [
    path('', views.stock_view, name='stock_view'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add/', views.add_stock_view, name='add_stock'),
    path('remove/', views.remove_stock_view, name='remove_stock'),
    path('transfer/', views.transfer_stock_view, name='transfer_stock'),
    path('transactions/', views.transactions_view, name='transactions'),
]
