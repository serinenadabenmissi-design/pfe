# ai_tracker/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('analyze/', views.analyze_food_image, name='analyze-food'),
    path('log-meal/', views.log_ai_meal, name='log-ai-meal'),
]