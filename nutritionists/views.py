#nutritionists/views.py
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DietPlan, Meal, PatientAssignment, Notification, PatientMealChecklist, SpecialOffer, PatientSubscription, AssignmentRequest
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from consultations.models import Consultation, ActivityLog
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import PatientProgress
from django.http import JsonResponse
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.contrib.auth import get_user_model
User = get_user_model()

def get_time_ago(dt):
    now = timezone.now()
    diff = now - dt
    if diff.days > 0:
        if diff.days == 1: return 'Yesterday'
        return f'{diff.days} days ago'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} hours ago'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} minutes ago'
    return 'Just now'

from datetime import date  

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_patients(request):
    # Utiliser profile.role au lieu de role directement
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    assignments = PatientAssignment.objects.filter(nutritionist=request.user, is_active=True).select_related('patient')
    patients_data = []
    for assignment in assignments:
        patient = assignment.patient
        profile = getattr(patient, 'profile', None)
        
        # Calculer l'âge à partir de date_of_birth si disponible
        age = 'N/A'
        if profile and profile.date_of_birth:
            today = date.today()
            age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
        
        active_plan = DietPlan.objects.filter(patient=patient, is_active=True).first()
        plan_name = active_plan.name if active_plan else 'No active plan'
        total_meals = PatientMealChecklist.objects.filter(patient=patient).count()
        completed_meals = PatientMealChecklist.objects.filter(patient=patient, status='completed').count()
        progress = round((completed_meals / total_meals) * 100) if total_meals > 0 else 0
        last_consultation = Consultation.objects.filter(patient=patient, nutritionist=request.user).order_by('-date').first()
        last_visit = last_consultation.date.strftime('%b %d, %Y') if last_consultation else 'No visits'
        patients_data.append({
            'id': patient.id, 
            'name': patient.get_full_name() or patient.email.split('@')[0], 
            'email': patient.email, 
            'age': age, 
            'plan': plan_name, 
            'progress': progress, 
            'last_visit': last_visit, 
            'avatar': patient.first_name[0] if patient.first_name else 'U'
        })
    return Response(patients_data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionist_stats(request):
    # Récupérer le rôle depuis le profile
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    nutritionist = request.user
    assignments = PatientAssignment.objects.filter(nutritionist=nutritionist, is_active=True).select_related('patient')
    patient_names = []
    adherence_rates = []
    
    for assignment in assignments:
        patient = assignment.patient
        patient_names.append(patient.get_full_name() or patient.email.split('@')[0])
        total_meals = PatientMealChecklist.objects.filter(patient=patient).count()
        completed_meals = PatientMealChecklist.objects.filter(patient=patient, status='completed').count()
        rate = round((completed_meals / total_meals) * 100) if total_meals > 0 else 0
        adherence_rates.append(rate)
    
    today = timezone.now().date()
    today_consultations = Consultation.objects.filter(nutritionist=nutritionist, date__date=today)
    today_count = today_consultations.count()
    completed_today = today_consultations.filter(status='completed').count()
    upcoming_today = today_consultations.filter(status='pending', date__gte=timezone.now()).count()
    
    recent_activities = ActivityLog.objects.filter(nutritionist=nutritionist)[:10]
    activities_list = [{'type': a.activity_type, 'description': a.description, 'time_ago': get_time_ago(a.created_at)} for a in recent_activities]
    if not activities_list:
        activities_list = [{'type': 'patient_assigned', 'description': 'New patient assigned', 'time_ago': '2 hours ago'}]
    
    return Response({
        'nutritionist_name': nutritionist.get_full_name() or nutritionist.email.split('@')[0],
        'specialization': getattr(nutritionist.profile, 'specialization', 'Clinical Nutritionist') if hasattr(nutritionist, 'profile') else 'Nutritionist',
        'email': nutritionist.email,
        'active_patients': len(patient_names),
        'active_patients_change': '+3 this month',
        'today_consultations': today_count,
        'today_consultations_detail': f'{completed_today} completed, {upcoming_today} upcoming',
        'pending_messages': 0,
        'earnings_mtd': 3240,
        'earnings_change': '+12% vs last month',
        'adherence_chart': {'labels': patient_names, 'rates': adherence_rates},
        'recent_activities': activities_list
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionist_profile(request):
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    user = request.user
    profile = getattr(user, 'profile', None)
    nutritionist_profile = getattr(user, 'nutritionist_profile', None)
    
    return Response({
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'phone': getattr(user, 'phone', ''),
        'specialization': profile.specialization if profile else '',
        'experience_years': nutritionist_profile.experience_years if nutritionist_profile else 0,
        'bio': nutritionist_profile.bio if nutritionist_profile else '',
        'is_available': nutritionist_profile.is_available if nutritionist_profile else True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_nutritionist_profile(request):
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    user = request.user
    data = request.data
    
    # Mettre à jour l'utilisateur
    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.save()
    
    # Mettre à jour UserProfile
    profile = user.profile
    profile.specialization = data.get('specialization', profile.specialization)
    profile.save()
    
    # Mettre à jour NutritionistProfile
    try:
        from consultations.models import NutritionistProfile
        nut_profile, created = NutritionistProfile.objects.get_or_create(user=user)
        nut_profile.bio = data.get('bio', nut_profile.bio)
        nut_profile.experience_years = data.get('experience_years', nut_profile.experience_years)
        nut_profile.is_available = data.get('is_available', nut_profile.is_available)
        if data.get('specialization'):
            nut_profile.specialization = data.get('specialization')
        nut_profile.save()
    except:
        pass
    
    return Response({'message': 'Profile updated successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    # Utiliser profile.role au lieu de role directement
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    notifications = Notification.objects.filter(nutritionist=request.user, is_read=False)[:20]
    return Response({
        'notifications': [{
            'id': n.id, 
            'type': n.notification_type, 
            'title': n.title, 
            'message': n.message, 
            'patient_name': n.related_patient.get_full_name() if n.related_patient else None, 
            'time_ago': get_time_ago(n.created_at), 
            'created_at': n.created_at.isoformat()
        } for n in notifications], 
        'unread_count': notifications.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, nutritionist=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    Notification.objects.filter(nutritionist=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionist_consultations(request):
    # Utiliser profile.role au lieu de role directement
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    now = timezone.now()
    upcoming = Consultation.objects.filter(nutritionist=request.user, status='confirmed', date__gte=now).order_by('date')
    past = Consultation.objects.filter(nutritionist=request.user, status='completed').order_by('-date')[:20]
    
    return Response({
        'upcoming': [{
            'id': c.id, 
            'patient_name': c.patient.get_full_name() or c.patient.email, 
            'date_display': c.date.strftime('%b %d, %Y • %I:%M %p'), 
            'date_iso': c.date.isoformat(), 
            'type': 'Zoom Call', 
            'zoom_link': c.zoom_link
        } for c in upcoming], 
        'past': [{
            'id': c.id, 
            'patient_name': c.patient.get_full_name() or c.patient.email, 
            'date_display': c.date.strftime('%b %d, %Y'), 
            'duration': '60 min', 
            'notes': c.nutritionist_notes
        } for c in past]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_details(request, patient_id):
    """Récupère les détails d'un patient assigné au nutritionniste"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    try:
        # Vérifier que le patient est bien assigné à ce nutritionniste
        is_assigned = PatientAssignment.objects.filter(
            nutritionist=request.user,
            patient_id=patient_id,
            is_active=True
        ).exists()
        
        if not is_assigned:
            return Response({'error': 'Patient not assigned to you'}, status=403)
        
        patient = User.objects.get(id=patient_id)
        profile = getattr(patient, 'profile', None)
        
        return Response({
            'id': patient.id,
            'name': patient.get_full_name() or patient.email.split('@')[0],
            'email': patient.email,
            'weight': profile.weight if profile else None,
            'height': profile.height if profile else None,
            'goal_weight': profile.goal if profile else None,
            'health_conditions': profile.health_conditions if profile else [],
            'plan': 'Active Plan',  # Tu peux récupérer le plan depuis l'abonnement
            'progress': 0,  # À calculer si besoin
            'last_visit': 'N/A',
            'created_at': patient.date_joined
        })
    except User.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=404)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_nutritionists(request):
    """Récupère les nutritionnistes avec moins de 4 patients actifs"""
    from accounts.models import CustomUser
    from nutritionists.models import PatientAssignment
    
    # Récupérer tous les utilisateurs avec role='nutritionist'
    nutritionists = CustomUser.objects.filter(profile__role='nutritionist')
    
    result = []
    for nut in nutritionists:
        active_patients_count = PatientAssignment.objects.filter(
            nutritionist=nut, 
            is_active=True
        ).count()
        
        # Afficher uniquement ceux avec moins de 4 patients
        if active_patients_count < 4:
            # Récupérer les infos du profil nutritionniste
            nut_profile = getattr(nut, 'nutritionist_profile', None)
            result.append({
                'id': nut.id,
                'full_name': nut.get_full_name() or nut.email.split('@')[0],
                'email': nut.email,
                'specialization': getattr(nut.profile, 'specialization', 'Nutritionist'),
                'bio': nut_profile.bio if nut_profile else 'Expert nutritionist ready to help you achieve your health goals.',
                'patients_count': active_patients_count,
                'max_patients': 4,
                'rating': 4.8,
                'experience_years': nut_profile.experience_years if nut_profile else 5,
                'avatar_color': '#27AE60'
            })
    
    return Response({'nutritionists': result})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_consultation(request, consultation_id):
    # Utiliser profile.role au lieu de role directement
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    try:
        consultation = Consultation.objects.get(id=consultation_id, nutritionist=request.user)
        consultation.status = 'completed'
        consultation.nutritionist_notes = request.data.get('notes', '')
        consultation.save()
        Notification.objects.create(
            user=consultation.patient, 
            notification_type='consultation_completed', 
            title='Consultation Completed', 
            message=f'Your consultation with {request.user.get_full_name()} on {consultation.date.strftime("%b %d")} has been marked as completed.', 
            related_id=consultation.id
        )
        return Response({'message': 'Consultation marked as completed'})
    except Consultation.DoesNotExist:
        return Response({'error': 'Consultation not found'}, status=404)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def create_diet_plan(request):
    if request.user.profile.role != 'nutritionist':
        return Response({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'GET':
        plans = DietPlan.objects.filter(nutritionist=request.user).order_by('-created_at')
        return Response([{'id': p.id, 'name': p.name, 'patient_name': p.patient.get_full_name() or p.patient.email.split('@')[0] if p.patient else 'Public Plan', 'start_date': p.start_date, 'end_date': p.end_date, 'is_active': p.is_active} for p in plans])
    
    elif request.method == 'POST':
        data = request.data
        plan_type = data.get('plan_type', 'personalized')
        
        if plan_type == 'personalized':
            plan = DietPlan.objects.create(nutritionist=request.user, patient_id=data['patient_id'], name=data['name'], description=data.get('description', ''), start_date=data['start_date'], end_date=data.get('end_date'), is_active=True)
            for meal_data in data.get('meals', []):
                Meal.objects.create(plan=plan, meal_type=meal_data['meal_type'], food_name=meal_data['food_name'], quantity=meal_data.get('quantity', ''), calories=meal_data.get('calories', 0), order=meal_data.get('order', 0))
            generate_meal_checklist(plan)
            Notification.objects.create(user=plan.patient, notification_type='plan_updated', title='New Diet Plan Assigned 🥗', message=f'{request.user.get_full_name()} has assigned you a new diet plan: "{plan.name}". Check your diet plans section!', related_id=plan.id)
            return Response({'message': 'Personalized plan created successfully', 'plan_id': plan.id}, status=201)
        
        elif plan_type == 'standard':
            special_offer = SpecialOffer.objects.create(name=data['name'], short_description=data.get('short_description', ''), description=data.get('description', ''), price=data['price'], original_price=data.get('original_price'), features=data.get('features', []), icon=data.get('icon', '🍽️'), offer_type='diet_plan', is_active=False, submitted_by=request.user, submitted_at=timezone.now(), valid_until=timezone.now().date() + timedelta(days=365))
            return Response({'message': 'Standard plan submitted for admin approval', 'offer_id': special_offer.id}, status=201)

def generate_meal_checklist(plan):
    current_date = plan.start_date
    end_date = plan.end_date or (plan.start_date + timedelta(days=30))
    while current_date <= end_date:
        for meal in plan.meals.all():
            PatientMealChecklist.objects.get_or_create(patient=plan.patient, meal=meal, date=current_date, defaults={'meal_name': f"{meal.get_meal_type_display()}: {meal.food_name}", 'meal_time': '12:00', 'status': 'pending'})
        current_date += timedelta(days=1)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patients_for_progress(request):
    # Utiliser profile.role au lieu de role directement
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    assignments = PatientAssignment.objects.filter(nutritionist=request.user, is_active=True).select_related('patient')
    return Response([{
        'id': a.patient.id, 
        'name': a.patient.get_full_name() or a.patient.email.split('@')[0]
    } for a in assignments])


@login_required
@require_http_methods(["GET"])
def get_patient_progress(request, patient_id):
    from users.models import WeightHistory
    try:
        is_assigned = PatientAssignment.objects.filter(nutritionist=request.user, patient_id=patient_id, is_active=True).exists()
        if not is_assigned:
            return JsonResponse({'error': 'Patient not assigned to you'}, status=403)
        patient = User.objects.get(id=patient_id)
        profile = getattr(patient, 'profile', None)
        weight_history = WeightHistory.objects.filter(user=patient).order_by('date')
        period = request.GET.get('period', '3m')
        period_days = {'1m': 30, '3m': 90, '6m': 180, '1y': 365, 'all': 9999}
        cutoff_days = period_days.get(period, 90)
        cutoff_date = timezone.now().date() - timedelta(days=cutoff_days)
        filtered = [entry for entry in weight_history if entry.date >= cutoff_date]
        
        if filtered:
            labels = [entry.date.strftime('%d/%m') for entry in filtered]
            weight_data = [float(entry.weight_kg) for entry in filtered]
            body_fat_data = [round(entry.weight_kg * 0.35, 1) for entry in filtered]
            current_weight = float(filtered[-1].weight_kg)
            first_weight = float(filtered[0].weight_kg)
            weight_change = round(current_weight - first_weight, 1)
            weight_change_percent = round(abs((weight_change / first_weight) * 100), 1) if first_weight > 0 else 0
            current_body_fat = body_fat_data[-1] if body_fat_data else None
            fat_change = round(current_body_fat - body_fat_data[0], 1) if current_body_fat else 0
        else:
            labels, weight_data, body_fat_data = [], [], []
            current_weight = float(profile.weight) if profile and profile.weight else None
            weight_change = 0
            current_body_fat = None
            fat_change = 0
        
        goal_weight = float(profile.goal) if profile and profile.goal else None
        to_goal = round(goal_weight - current_weight, 1) if goal_weight and current_weight else 0
        
        return JsonResponse({'labels': labels, 'weight_data': weight_data, 'body_fat_data': body_fat_data, 'current_weight': current_weight, 'current_body_fat': current_body_fat, 'goal_weight': goal_weight, 'weight_change': weight_change, 'weight_change_percent': weight_change_percent, 'fat_change': fat_change, 'to_goal': to_goal, 'to_goal_text': f'{abs(to_goal)} kg to goal' if goal_weight else 'No goal set'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_special_offers(request):
    diet_plans = SpecialOffer.objects.filter(is_active=True, offer_type='diet_plan').order_by('-featured', 'price')
    seasonal_offers = SpecialOffer.objects.filter(is_active=True, offer_type='seasonal', valid_until__gte=timezone.now().date()).order_by('-featured', '-discount_percent')
    return Response({'diet_plans': [{'id': o.id, 'name': o.name, 'description': o.description, 'price': float(o.price), 'original_price': float(o.original_price) if o.original_price else None, 'discount_percent': o.discount_percent, 'image_url': o.image_url, 'valid_until': o.valid_until.isoformat(), 'featured': o.featured, 'icon': o.icon, 'features': o.features} for o in diet_plans], 'seasonal_offers': [{'id': o.id, 'name': o.name, 'description': o.description, 'price': float(o.price), 'original_price': float(o.original_price) if o.original_price else None, 'discount_percent': o.discount_percent, 'image_url': o.image_url, 'valid_until': o.valid_until.isoformat(), 'days_left': (o.valid_until - timezone.now().date()).days, 'icon': o.icon, 'features': o.features} for o in seasonal_offers]})

from django.http import HttpResponse
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_offer(request, offer_id):
    try:
        offer = SpecialOffer.objects.get(id=offer_id, is_active=True)
        patient = request.user
        profile = patient.user_profile
        
        is_premium = (offer_id == 2) or (offer.name and offer.name.lower() == 'premium')
        duration_months = request.data.get('duration_months', 1)
        include_ai = request.data.get('include_ai', False)
        include_consultations = request.data.get('include_consultations', False)
        
        if is_premium:
            include_ai = True
            include_consultations = True
        
        duration_days = duration_months * 30
        
        if offer.offer_type == 'seasonal' and offer.valid_until < timezone.now().date():
            return Response({'error': 'This offer has expired'}, status=400)
        
        PatientSubscription.objects.filter(patient=patient, status='active').update(status='expired')
        DietPlan.objects.filter(patient=patient, is_active=True).update(is_active=False)
        
        subscription = PatientSubscription.objects.create(patient=patient, special_offer=offer, plan_name=offer.name, price_paid=request.data.get('total_price', offer.price), duration_months=duration_months, start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=duration_days), status='active', auto_renew=False)
        
        profile.has_diet_plan = True
        profile.has_ai_tracker = include_ai
        profile.has_consultations = include_consultations
        profile.payment_completed = True
        profile.payment_date = timezone.now()
        
        if is_premium:
            profile.subscription_plan = 'premium'
        elif include_consultations:
            profile.subscription_plan = 'premium'
        else:
            profile.subscription_plan = 'standard'
        profile.save()
        
        if offer.offer_type == 'diet_plan':
            nutritionist = offer.diet_plan.nutritionist if offer.diet_plan and offer.diet_plan.nutritionist else User.objects.filter(role='nutritionist').first()
            new_plan = DietPlan.objects.create(nutritionist=nutritionist, patient=patient, name=offer.name, description=offer.description, start_date=timezone.now().date(), end_date=subscription.end_date, is_active=True)
            if offer.diet_plan:
                for meal in offer.diet_plan.meals.all():
                    Meal.objects.create(plan=new_plan, meal_type=meal.meal_type, food_name=meal.food_name, quantity=meal.quantity, calories=meal.calories, order=meal.order)
        
        if is_premium or (include_consultations and not is_premium):
            request.session['pending_consultation'] = {'subscription_id': subscription.id, 'plan_name': offer.name, 'duration': duration_months, 'patient_id': patient.id}
            return Response({'success': True, 'message': 'Plan activated! Please select your nutritionist.', 'redirect': '/select-nutritionist/', 'subscription_plan': 'premium' if (is_premium or include_consultations) else 'standard', 'has_consultations': True, 'has_ai': include_ai or is_premium, 'need_nutritionist': True})
        elif include_ai and not include_consultations:
            return Response({'success': True, 'message': f'✅ {offer.name} + AI Tracking activated successfully!', 'redirect': '/user-profile/', 'subscription_plan': 'standard', 'has_ai': True, 'has_consultations': False})
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#27AE60'))
            story.append(Paragraph(f"🍽️ {offer.name}", title_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph(offer.description, styles['Normal']))
            story.append(Spacer(1, 12))
            story.append(Paragraph("<b>What's included:</b>", styles['Heading2']))
            for feature in offer.features:
                story.append(Paragraph(f"✅ {feature}", styles['Normal']))
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"<b>Patient:</b> {patient.get_full_name()}", styles['Normal']))
            story.append(Paragraph(f"<b>Email:</b> {patient.email}", styles['Normal']))
            story.append(Paragraph(f"<b>Date:</b> {timezone.now().strftime('%d %B %Y')}", styles['Normal']))
            story.append(Paragraph(f"<b>Valid until:</b> {subscription.end_date.strftime('%d %B %Y')}", styles['Normal']))
            doc.build(story)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="diet_plan_{subscription.id}.pdf"'
            return response
    except SpecialOffer.DoesNotExist:
        return Response({'error': 'Offer not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignment_requests(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    requests = AssignmentRequest.objects.filter(status='pending').select_related('patient', 'nutritionist').order_by('-created_at')
    return Response({'requests': [{'id': r.id, 'patient_id': r.patient.id, 'patient_name': r.patient.get_full_name() or r.patient.email.split('@')[0], 'patient_email': r.patient.email, 'requested_nutritionist_id': r.nutritionist.id, 'requested_nutritionist_name': r.nutritionist.get_full_name() or r.nutritionist.email.split('@')[0], 'order_data': getattr(r, 'order_data', {}), 'created_at': r.created_at.isoformat(), 'created_at_display': r.created_at.strftime('%d %b %Y, %H:%M')} for r in requests]})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_assignment_request(request, request_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    try:
        assignment_request = AssignmentRequest.objects.get(id=request_id, status='pending')
    except AssignmentRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=404)
    
    action = request.data.get('action')
    alternative_nutritionist_id = request.data.get('alternative_nutritionist_id')
    reason = request.data.get('reason', '')
    
    if action == 'approve':
        if alternative_nutritionist_id and alternative_nutritionist_id != '':
            try:
                nutritionist = User.objects.get(id=alternative_nutritionist_id, role='nutritionist')
            except User.DoesNotExist:
                return Response({'error': 'Alternative nutritionist not found'}, status=404)
        else:
            nutritionist = assignment_request.nutritionist
        
        PatientAssignment.objects.filter(patient=assignment_request.patient, is_active=True).update(is_active=False)
        PatientAssignment.objects.create(patient=assignment_request.patient, nutritionist=nutritionist, is_active=True)
        
        profile = assignment_request.patient.user_profile
        if profile:
            profile.has_consultations = True
            profile.has_diet_plan = True
            profile.payment_completed = True
            if hasattr(assignment_request, 'order_data') and assignment_request.order_data:
                profile.subscription_plan = assignment_request.order_data.get('planName', 'premium').lower()
            else:
                profile.subscription_plan = 'premium'
            profile.save()
        
        assignment_request.status = 'approved'
        assignment_request.save()
        
        Notification.objects.create(user=assignment_request.patient, notification_type='assignment_approved', title='✅ Nutritionist Assigned!', message=f'Your request has been approved. You are now assigned to {nutritionist.get_full_name() or nutritionist.email}. You can now send messages and book consultations.', related_id=nutritionist.id, is_read=False)
        Notification.objects.create(nutritionist=nutritionist, notification_type='new_patient_assigned', title='👤 New Patient Assigned', message=f'{assignment_request.patient.get_full_name() or assignment_request.patient.email} has been assigned to you by admin.', related_patient=assignment_request.patient, related_id=assignment_request.patient.id, is_read=False)
        
        return Response({'success': True, 'message': f'Request approved! {nutritionist.get_full_name()} assigned to patient.', 'assigned_nutritionist': nutritionist.get_full_name()})
    
    elif action == 'reject':
        assignment_request.status = 'rejected'
        assignment_request.rejection_reason = reason
        assignment_request.save()
        Notification.objects.create(user=assignment_request.patient, notification_type='assignment_rejected', title='❌ Nutritionist Request Update', message=f'Your request for {assignment_request.nutritionist.get_full_name()} was not approved. Reason: {reason}. Please contact support for assistance or try another nutritionist.', related_id=assignment_request.id, is_read=False)
        return Response({'success': True, 'message': 'Request rejected. Patient has been notified.'})
    
    return Response({'error': 'Invalid action'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_nutritionists(request):
    """Récupère les nutritionnistes avec moins de 4 patients actifs"""
    from django.db import models
    from accounts.models import CustomUser
    from nutritionists.models import PatientAssignment
    
    # Récupérer tous les utilisateurs avec role='nutritionist' dans leur profile
    nutritionists = CustomUser.objects.filter(profile__role='nutritionist')
    
    result = []
    for nut in nutritionists:
        active_patients_count = PatientAssignment.objects.filter(
            nutritionist=nut, 
            is_active=True
        ).count()
        
        # Afficher uniquement ceux avec moins de 4 patients
        if active_patients_count < 4:
            result.append({
                'id': nut.id,
                'full_name': nut.get_full_name() or nut.email.split('@')[0],
                'email': nut.email,
                'specialization': getattr(nut.profile, 'specialization', 'Nutritionist'),
                'bio': 'Expert nutritionist ready to help you achieve your health goals.',
                'patients_count': active_patients_count,
                'max_patients': 4,
                'rating': 4.8,
                'experience_years': 5,
                'avatar_color': '#27AE60'
            })
    
    return Response({'nutritionists': result})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_diet_plan_to_patient(request):
    """Envoyer un plan diététique à un patient avec génération de la checklist"""
    from django.utils import timezone
    from datetime import date, timedelta
    from .models import PatientMealChecklist
    
    # Vérifier que l'utilisateur est un nutritionniste
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized - You are not a nutritionist'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    data = request.data
    patient_id = data.get('patient_id')
    plan_name = data.get('plan_name')
    description = data.get('description', '')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    duration_weeks = data.get('duration_weeks', 4)
    weekly_program = data.get('weekly_program', {})
    sport_advice = data.get('sport_advice', '')
    extra_tips = data.get('extra_tips', '')
    
    if not patient_id or not plan_name or not start_date:
        return Response({'error': 'Missing required fields: patient_id, plan_name, start_date'}, status=400)
    
    try:
        patient = User.objects.get(id=patient_id)
    except User.DoesNotExist:
        return Response({'error': f'Patient with id {patient_id} not found'}, status=404)
    
    # 1. Créer le plan diététique
    full_description = description
    if sport_advice:
        full_description += f"\n\n🏋️ Conseils sport: {sport_advice}"
    if extra_tips:
        full_description += f"\n\n💡 Astuces: {extra_tips}"
    
    diet_plan = DietPlan.objects.create(
        nutritionist=request.user,
        patient=patient,
        name=plan_name,
        description=full_description,
        start_date=start_date,
        end_date=end_date if end_date else None,
        is_active=True
    )
    
    # 2. Ajouter les repas
    meal_order = 0
    meal_type_map = {
        'breakfast': 'breakfast',
        'lunch': 'lunch',
        'snack': 'snack',
        'dinner': 'dinner'
    }
    
    # Stocker les repas créés pour la checklist
    created_meals = []
    
    for day, meals in weekly_program.items():
        for meal_type, meal_list in meals.items():
            mapped_type = meal_type_map.get(meal_type, meal_type)
            for meal_item in meal_list:
                if isinstance(meal_item, dict) and meal_item.get('food'):
                    meal = Meal.objects.create(
                        plan=diet_plan,
                        meal_type=mapped_type,
                        food_name=meal_item.get('food', ''),
                        quantity='1 portion',
                        calories=meal_item.get('calories', 0),
                        order=meal_order
                    )
                    created_meals.append(meal)
                    meal_order += 1
    
    # 3. GÉNÉRER LA CHECKLIST DES REPAS POUR CHAQUE JOUR
    # Calculer la date de fin du plan (start_date + duration_weeks semaines)
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    except:
        start_date_obj = date.today()
    
    # Si end_date non fournie, calculer à partir de la durée
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except:
            end_date_obj = start_date_obj + timedelta(weeks=int(duration_weeks))
    else:
        end_date_obj = start_date_obj + timedelta(weeks=int(duration_weeks))
    
    # Générer la checklist pour chaque jour entre start_date et end_date
    current_date = start_date_obj
    while current_date <= end_date_obj:
        for meal in created_meals:
            # Nom du repas formaté
            meal_type_display = dict(Meal.MEAL_TYPES).get(meal.meal_type, meal.meal_type)
            meal_name = f"{meal_type_display}: {meal.food_name}"
            
            # Heure par défaut selon le type de repas
            meal_time_map = {
                'breakfast': '08:00',
                'lunch': '12:30',
                'snack': '16:00',
                'dinner': '19:30'
            }
            meal_time = meal_time_map.get(meal.meal_type, '12:00')
            
            PatientMealChecklist.objects.get_or_create(
                patient=patient,
                meal=meal,
                date=current_date,
                defaults={
                    'meal_name': meal_name,
                    'meal_time': meal_time,
                    'calories': meal.calories,
                    'status': 'pending'
                }
            )
        current_date += timedelta(days=1)
    
    # 4. Créer une notification pour le patient
    try:
        Notification.objects.create(
            user=patient,
            notification_type='plan_updated',
            title='📋 Nouveau plan diététique reçu !',
            message=f'Votre nutritionniste {request.user.get_full_name() or request.user.email} vous a envoyé un nouveau plan : "{plan_name}". Les repas du jour sont disponibles dans "Today\'s Meals Checklist" !',
            related_id=diet_plan.id,
            is_read=False
        )
    except Exception as e:
        print(f"Error creating notification: {e}")
    
    return Response({
        'success': True,
        'message': f'Plan "{plan_name}" envoyé à {patient.get_full_name() or patient.email} avec sa checklist générée',
        'plan_id': diet_plan.id,
        'meals_count': len(created_meals)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_standard_plan(request):
    """Soumettre un plan standard pour validation admin"""
    if request.user.profile.role != 'nutritionist':
        return Response({'error': 'Unauthorized'}, status=403)
    
    data = request.data
    plan_name = data.get('plan_name')
    description = data.get('description', '')
    duration_weeks = data.get('duration_weeks', 4)
    weekly_program = data.get('weekly_program', {})
    sport_advice = data.get('sport_advice', '')
    
    if not plan_name:
        return Response({'error': 'Plan name is required'}, status=400)
    
    # Créer le special offer en attente d'approbation
    special_offer = SpecialOffer.objects.create(
        name=plan_name,
        description=description,
        short_description=description[:100] if description else '',
        price=0,
        offer_type='diet_plan',
        features=['Programme sur mesure', 'Repas équilibrés', 'Conseils sportifs'],
        icon='🍽️',
        is_active=False,
        submitted_by=request.user,
        submitted_at=timezone.now(),
        valid_until=timezone.now().date() + timedelta(days=365),
        extra_data={  # ← UTILISE extra_data
            'duration_weeks': duration_weeks,
            'weekly_program': weekly_program,
            'sport_advice': sport_advice,
            'submitted_by_name': request.user.get_full_name() or request.user.email
        }
    )
    print(f"SpecialOffer créé: id={special_offer.id}, is_active={special_offer.is_active}")
    
    # Créer une notification pour l'admin
    Notification.objects.create(
        nutritionist=None,
        notification_type='admin_notification',
        title='📋 New Standard Plan Submitted',
        message=f'Nutritionist {request.user.get_full_name() or request.user.email} has submitted a new standard plan: "{plan_name}". Please review and approve.',
        related_id=special_offer.id,
        is_read=False,
        is_admin_notification=True
    )
    
    return Response({
        'success': True,
        'message': f'Standard plan "{plan_name}" submitted for admin approval',
        'offer_id': special_offer.id
    })