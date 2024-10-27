# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main view for uploading and processing
    path('', views.ProcessorView.as_view(), name='home'),
    
    # API endpoints
    path('process/', views.process_pdf, name='process'),
    path('test-api/', views.test_gemini, name='test_api'),
    
    # Results view
    path('results/<int:job_id>/', views.ResultsView.as_view(), name='results'),
]