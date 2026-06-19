# nutritionists/admin.py
from django.contrib import admin
from .models import DietPlan, Meal, PatientMealChecklist, PatientAssignment, Notification, PatientProgress, SpecialOffer, PatientSubscription, AssignmentRequest

# Enregistre les modèles de nutritionists
models_list = [
    DietPlan, Meal, PatientMealChecklist, PatientAssignment,
    Notification, PatientProgress, SpecialOffer, PatientSubscription, AssignmentRequest
]

for model in models_list:
    try:
        admin.site.register(model)
    except:
        pass