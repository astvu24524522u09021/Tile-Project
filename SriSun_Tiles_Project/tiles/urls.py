from django.urls import path

from . import views

urlpatterns = [
    path('', views.tile_list_view, name='tile_list'),
    path('search/', views.tile_list_view, name='tile_search'),
    path('scan/', views.tile_scan_view, name='tile_scan'),
    path('new/', views.tile_create_view, name='tile_create'),
    path('<int:pk>/', views.tile_detail_view, name='tile_detail'),
    path('<int:pk>/edit/', views.tile_update_view, name='tile_update'),
    path('<int:pk>/delete/', views.tile_delete_view, name='tile_delete'),
]
