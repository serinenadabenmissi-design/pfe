# consultations/admin.py
from django.contrib import admin
from .models import Consultation, WeeklyReport, NutritionistProfile, ActivityLog

models_list = [Consultation, WeeklyReport, NutritionistProfile, ActivityLog]

for model in models_list:
    try:
        admin.site.register(model)
    except:
        pass