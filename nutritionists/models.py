#nutritionists/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings

class DietPlan(models.Model):
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_plans', limit_choices_to={'role': 'nutritionist'})
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_plans', limit_choices_to={'role': 'patient'})
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_seasonal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Meal(models.Model):
    MEAL_TYPES = [('breakfast', 'Petit-déjeuner'), ('lunch', 'Déjeuner'), ('dinner', 'Dîner'), ('snack', 'Collation')]
    plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    food_name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=100)
    calories = models.IntegerField()
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['plan', 'meal_type', 'order']

class PatientMealChecklist(models.Model):
    STATUS_CHOICES = [('pending', 'À faire'), ('completed', 'Fait'), ('skipped', 'Sauté')]
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_checklists')
    meal = models.ForeignKey('Meal', on_delete=models.CASCADE, related_name='nutritionist_meal_checklists', null=True, blank=True)
    meal_name = models.CharField(max_length=200)
    meal_time = models.CharField(max_length=20, default='12:00')
    calories = models.IntegerField(default=0)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['patient', 'meal_name', 'date']
        ordering = ['date', 'meal_time']

        
class PatientAssignment(models.Model):
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_patients', limit_choices_to={'role': 'nutritionist'})
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_nutritionist', limit_choices_to={'role': 'patient'})
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['nutritionist', 'patient']

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('patient_assigned', 'Nouveau patient'),
        ('consultation_reminder', 'Rappel consultation'),
        ('new_message', 'Nouveau message'),
        ('plan_updated', 'Plan mis à jour'),
        ('blog_pending', 'Blog Pending'),
        ('blog_update', 'Blog Update'),
        ('assignment_request', 'Demande d\'assignation'),
        ('assignment_approved', 'Assignation approuvée'),
        ('assignment_rejected', 'Assignation refusée'),
        ('admin_notification', 'Notification Admin'),
    ]
    
    # ← AJOUTE related_name différents pour éviter le conflit
    nutritionist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nutritionist_notifications',  # ← Changé
        limit_choices_to={'role': 'nutritionist'},
        null=True,
        blank=True
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_notifications',  # ← Changé
        null=True,
        blank=True
    )
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='+'
    )
    related_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_admin_notification = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class PatientProgress(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_records')
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_progress', null=True, blank=True)
    date = models.DateField(default=timezone.now)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    body_fat = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    muscle_mass = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']

class SpecialOffer(models.Model):
    OFFER_TYPES = [('diet_plan', 'Diet Plan'), ('seasonal', 'Seasonal Offer')]
    name = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    discount_percent = models.IntegerField(default=0)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES, default='diet_plan')
    features = models.JSONField(default=list)
    icon = models.CharField(max_length=10, default='🍽️')
    diet_plan = models.ForeignKey(DietPlan, on_delete=models.SET_NULL, null=True, blank=True)
    valid_until = models.DateField()
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_offers')
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(default=dict, blank=True, null=True)

class PatientSubscription(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled')]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    special_offer = models.ForeignKey(SpecialOffer, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    plan_name = models.CharField(max_length=200)
    price_paid = models.DecimalField(max_digits=8, decimal_places=2)
    duration_months = models.IntegerField(default=1)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    plan_type = models.CharField(max_length=20, choices=[
        ('standard', 'Standard'),
        ('premium', 'Premium')
    ], default='standard')

    class Meta:
        ordering = ['-created_at']
    
    @property
    def is_active(self):
        return self.status == 'active' and self.end_date >= timezone.now().date()
    
    @property
    def days_left(self):
        if self.status == 'active' and self.end_date >= timezone.now().date():
            return (self.end_date - timezone.now().date()).days
        return 0

class AssignmentRequest(models.Model):
    STATUS_CHOICES = [('pending', 'En attente'), ('approved', 'Approuvé'), ('rejected', 'Refusé'), ('cancelled', 'Annulé')]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignment_requests')
    nutritionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignment_requests_received')
    order_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']