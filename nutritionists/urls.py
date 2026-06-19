from django.urls import path
from . import views

urlpatterns = [
    path('my-patients/', views.get_my_patients, name='my-patients'),
    path('stats/', views.get_nutritionist_stats, name='nutritionist-stats'),
    path('notifications/', views.get_notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark-read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='read-all'),
    path('consultations/', views.get_nutritionist_consultations, name='nutritionist-consultations'),
    path('consultations/<int:consultation_id>/complete/', views.complete_consultation, name='complete-consultation'),
    path('diet-plans/', views.create_diet_plan, name='create-diet-plan'),
    path('patients-progress/', views.get_patients_for_progress, name='patients-progress'),
    path('patient-progress/<int:patient_id>/', views.get_patient_progress, name='patient-progress'),
    path('special-offers/', views.get_special_offers, name='special-offers'),
    path('purchase-offer/<int:offer_id>/', views.purchase_offer, name='purchase-offer'),
    path('assignment-requests/', views.get_assignment_requests, name='assignment_requests'),
    path('assignment-requests/<int:request_id>/handle/', views.handle_assignment_request, name='handle_assignment_request'),
    path('available/', views.get_available_nutritionists, name='available-nutritionists'),
    path('update-profile/', views.update_nutritionist_profile, name='update-nutritionist-profile'),
    path('my-patients/', views.get_my_patients, name='my-patients'),
    path('profile/', views.get_nutritionist_profile, name='nutritionist-profile'),
    path('available/', views.get_available_nutritionists, name='available-nutritionists'),
    path('patient-details/<int:patient_id>/', views.get_patient_details, name='patient-details-nutritionist'),
    path('send-diet-plan/', views.send_diet_plan_to_patient, name='send-diet-plan'),
    path('submit-standard-plan/', views.submit_standard_plan, name='submit-standard-plan'),
]