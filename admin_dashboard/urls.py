from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.get_all_users, name='all-users'),
    path('assign-patient/', views.assign_patient_to_nutritionist, name='assign-patient'),
    path('block-user/<int:user_id>/', views.block_user, name='block-user'),
    path('create-patient/', views.create_patient, name='create-patient'),
    path('nutritionists/', views.get_all_nutritionists, name='all-nutritionists'),
    path('create-nutritionist/', views.create_nutritionist, name='create-nutritionist'),
    path('nutritionist-status/<int:nutritionist_id>/', views.update_nutritionist_status, name='nutritionist-status'),
    path('delete-nutritionist/<int:nutritionist_id>/', views.delete_nutritionist, name='delete-nutritionist'),
    path('stats/', views.get_admin_stats, name='admin-stats'),
    path('trial-requests/', views.get_trial_requests, name='trial-requests'),
    path('trial-stats/', views.get_trial_stats, name='trial-stats'),
    path('handle-trial-request/<int:request_id>/', views.handle_trial_request, name='handle-trial-request'),
    path('subscriptions/', views.get_all_subscriptions, name='subscriptions'),
    path('assignment-requests/', views.get_assignment_requests_admin, name='assignment-requests'),
    path('assignment-requests/<int:request_id>/handle/', views.handle_assignment_request_admin, name='handle-assignment'),
    path('assignment-stats/', views.get_assignment_stats, name='assignment-stats'),
    path('recent-activities/', views.get_recent_activities, name='recent-activities'),
    path('notifications/read-all/', views.mark_all_admin_notifications_read, name='admin-notifications-read-all'),
    path('notifications/', views.get_admin_notifications, name='admin-notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_admin_notification_read, name='admin-notification-read'),
    path('pending-standard-plans/', views.get_pending_standard_plans, name='pending-standard-plans'),
    path('approve-standard-plan/<int:plan_id>/', views.approve_standard_plan, name='approve-standard-plan'),
    path('reject-standard-plan/<int:plan_id>/', views.reject_standard_plan, name='reject-standard-plan'),
    path('all-diet-plans/', views.get_all_diet_plans, name='all-diet-plans'),

]