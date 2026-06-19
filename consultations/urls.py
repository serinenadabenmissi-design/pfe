# consultations/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs
    path('nutritionists/', views.get_nutritionists, name='nutritionists'),
    path('nutritionist-profile/', views.get_nutritionist_profile, name='nutritionist-profile'),
    path('my-consultations/', views.get_my_consultations, name='my-consultations'),
    path('book/', views.book_consultation, name='book-consultation'),
    path('cancel/<int:consultation_id>/', views.cancel_consultation, name='cancel-consultation'),
    path('book-trial/', views.book_trial_consultation, name='book-trial'),
    path('trial-status/', views.get_trial_status, name='trial-status'),
    path('request-nutritionist-assignment/', views.request_nutritionist_assignment, name='request-nutritionist-assignment'),
    
    # NEW URLs for Nutritionist Consultation Management
    path('pending-requests/', views.get_pending_requests, name='pending-requests'),
    path('upcoming/', views.get_upcoming_consultations, name='upcoming-consultations'),
    path('completed/', views.get_completed_consultations, name='completed-consultations'),
    path('weekly/', views.get_weekly_consultation_counts, name='weekly-consultations'),
    path('by-date/', views.get_consultations_by_date, name='consultations-by-date'),
    path('<int:consult_id>/respond/', views.respond_to_consultation, name='respond-consultation'),
    path('<int:consult_id>/update/', views.update_consultation, name='update-consultation'),
    path('<int:consult_id>/complete/', views.complete_consultation, name='complete-consultation'),
    path('trial-requests/', views.get_trial_requests, name='get_trial_requests'),
]