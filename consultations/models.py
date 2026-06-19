# consultations/models.py
from django.db import models
from django.conf import settings
import uuid

class Consultation(models.Model):
    STATUS_CHOICES = [('requested', 'Demandée'), ('pending', 'Pending'), ('confirmed', 'Confirmed'), ('completed', 'Completed'), ('canceled', 'Canceled'), ('rejected', 'Refusée')]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consultations_as_patient', limit_choices_to={'role': 'patient'}, null=True, blank=True)
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consultations_as_nutritionist', limit_choices_to={'role': 'nutritionist'}, null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    nutritionist_notes = models.TextField(blank=True, null=True)
    zoom_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    trial_confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    class Meta:
        ordering = ['date']

class WeeklyReport(models.Model):
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reports', limit_choices_to={'role': 'nutritionist'})
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reports')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class NutritionistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nutritionist_profile')
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    experience_years = models.IntegerField(default=0)
    photo = models.ImageField(upload_to='nutritionists/', null=True, blank=True)
    is_available = models.BooleanField(default=True)

class ActivityLog(models.Model):
    ACTIVITY_TYPES = [('patient_assigned', 'Patient Assigné'), ('consultation_completed', 'Consultation Terminée'), ('message_sent', 'Message Envoyé'), ('plan_updated', 'Plan Mis à Jour')]
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    related_patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']