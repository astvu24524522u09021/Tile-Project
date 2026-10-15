from django.urls import path

from . import views

urlpatterns = [
    path('', views.assistant_view, name='assistant'),
    path('search/', views.assistant_view, name='ai_search'),
]
