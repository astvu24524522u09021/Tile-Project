from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from inventory.views import dashboard_view
from tiles import views as tile_views

urlpatterns = [
    path('admin/dashboard/', dashboard_view, name='admin_dashboard'),
    path('admin/products/', tile_views.tile_admin_list_view, name='admin_product_list'),
    path('admin/products/add/', tile_views.tile_create_view, name='admin_tile_create'),
    path('admin/products/<int:pk>/edit/', tile_views.tile_update_view, name='admin_tile_update'),
    path('admin/products/<int:pk>/delete/', tile_views.tile_delete_view, name='admin_tile_delete'),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('tiles/', include('tiles.urls')),
    path('inventory/', include('inventory.urls')),
    path('ai/', include('ai_features.urls')),
    path('ml/', include('ml_features.urls')),
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
