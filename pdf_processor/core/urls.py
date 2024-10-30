# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.ProcessorView.as_view(), name='home'),
    path('process-pdf/', views.ProcessorView.as_view(), name='process-pdf'),
    path('test-api/', views.test_gemini, name='test_api'),
]