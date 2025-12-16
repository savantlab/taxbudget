from django.urls import path
from . import views

urlpatterns = [
    path('', views.allocate_view, name='allocate'),
    path('results/<str:session_key>/', views.results_view, name='results'),
    path('aggregate/', views.aggregate_view, name='aggregate'),
    path('history/', views.history_view, name='history'),
]
