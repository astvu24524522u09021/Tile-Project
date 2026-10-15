from django.urls import path

from . import views

urlpatterns = [
    path('', views.prediction_view, name='prediction'),
    path('results/', views.prediction_result_view, name='prediction_results'),
]
