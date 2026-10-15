from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('customer-dashboard/', views.customer_dashboard_view, name='legacy_customer_dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
