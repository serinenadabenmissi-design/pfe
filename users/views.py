# users/views.py
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UserProfile, WeightHistory
from datetime import date
from django.views.decorators.csrf import csrf_exempt 
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt 
def get_profile_stats(request):
    profile = request.user.profile
    user = request.user
    weight_history = WeightHistory.objects.filter(user=request.user).order_by('-date')[:6]
    
    timeline = []
    for entry in reversed(weight_history):
        timeline.append({
            'date': entry.date.strftime('%b %d'),
            'weight': entry.weight_kg,
            'bmi': round(entry.weight_kg / ((profile.height / 100) ** 2), 1)
        })
    
    if not timeline:
        current_bmi = profile.get_bmi()
        timeline.append({
            'date': date.today().strftime('%b %d'),
            'weight': profile.weight,
            'bmi': current_bmi
        })

    weight_change = 0
    if weight_history.count() >= 2:
        latest = weight_history.first()
        previous = weight_history[1]
        weight_change = round(latest.weight_kg - previous.weight_kg, 1)
    
    # ✅ Calcul du health_score basé sur l'IMC
    bmi = profile.get_bmi()
    if 18.5 <= bmi <= 25:
        health_score = 90
    elif 25 < bmi <= 30:
        health_score = 70
    elif bmi > 30:
        health_score = 50
    else:
        health_score = 60
    
    return Response({
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'streak': profile.nutrition_streak,
        'health_score': health_score,  # ✅ Maintenant défini
        'bmi': bmi,
        'bmi_category': profile.get_bmi_category(),
        'height': profile.height,
        'current_weight': profile.weight,
        'goal': profile.goal,
        'health_conditions': profile.health_conditions if hasattr(profile, 'health_conditions') else [], 
        'weight_change': weight_change,
        'timeline': timeline
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.profile.role if hasattr(user, 'profile') else 'client'
    }) 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_weight(request):
    new_weight = request.data.get('weight')
    if not new_weight:
        return Response({'error': 'Weight required'}, status=400)
    
   
    profile = request.user.profile
    WeightHistory.objects.create(user=request.user, weight_kg=profile.weight)
    profile.weight = float(new_weight)
    profile.save()
    
    return Response({
        'message': 'Weight updated',
        'new_bmi': profile.get_bmi(),
        'new_bmi_category': profile.get_bmi_category(),
        'health_score': profile.get_health_score()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_streak(request):
    from datetime import date, timedelta
    
    profile = request.user.profile
    today = date.today()
    
    if profile.last_streak_date == today:
        return Response({'streak': profile.nutrition_streak, 'already': True})
    
    if profile.last_streak_date == today - timedelta(days=1):
        profile.nutrition_streak += 1
    else:
        profile.nutrition_streak = 1
    
    profile.last_streak_date = today
    profile.save()
    return Response({'streak': profile.nutrition_streak})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weight_history(request):
    weight_history = WeightHistory.objects.filter(user=request.user).order_by('date')[:30]
   
    goal_weight = request.user.profile.goal if hasattr(request.user.profile, 'goal') else None
    return Response({
        'labels': [entry.date.strftime('%d/%m') for entry in weight_history],
        'weights': [entry.weight_kg for entry in weight_history],
        'goal_weight': goal_weight,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_achievements(request):
    try:
        # ✅ CORRECTION
        profile = request.user.profile
        streak = profile.nutrition_streak if profile.nutrition_streak else 0
        consultations_count = 0
        try:
            from consultations.models import Consultation
            consultations_count = Consultation.objects.filter(patient=request.user, status='completed').count()
        except:
            consultations_count = 0
        
        achievements = [
            {'icon': '🔥' if streak >= 7 else '⏳', 'text': f'{streak}-day streak tracking meals', 'completed': streak >= 7, 'progress': f'{streak}/7' if streak < 7 else None},
            {'icon': '✅' if consultations_count >= 1 else '📅', 'text': 'Complete your first consultation', 'completed': consultations_count >= 1, 'progress': None},
            {'icon': '🏅', 'text': 'Walked 8k steps avg last week', 'completed': False, 'progress': '5.2k/8k'}
        ]
        return Response({'streak': streak, 'consultations_count': consultations_count, 'achievements': achievements})
    except Exception as e:
        return Response({'streak': 0, 'consultations_count': 0, 'achievements': [{'icon': '⏳', 'text': 'Start tracking your progress', 'completed': False}]}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weekly_report(request):
    from consultations.models import WeeklyReport
    latest_report = WeeklyReport.objects.filter(patient=request.user).order_by('-created_at').first()
    if latest_report:
        return Response({'has_report': True, 'content': latest_report.content, 'nutritionist_name': latest_report.nutritionist.get_full_name(), 'date': latest_report.created_at.strftime('%d %B %Y')})
    return Response({'has_report': False, 'message': 'No weekly report yet. Your nutritionist will provide feedback soon.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_calendar(request):
    from consultations.models import Consultation
    from nutritionists.models import PatientMealChecklist
    from django.utils import timezone
    
    consultations = Consultation.objects.filter(patient=request.user, status='confirmed', date__gte=timezone.now().date()).order_by('date')
    meals = PatientMealChecklist.objects.filter(patient=request.user, status='pending', date__gte=timezone.now().date()).order_by('date')[:30]
    
    meals_by_date = {}
    for meal in meals:
        date_str = meal.date.isoformat()
        if date_str not in meals_by_date:
            meals_by_date[date_str] = []
        meals_by_date[date_str].append({'name': meal.meal_name, 'time': meal.meal_time if hasattr(meal, 'meal_time') else '12:00'})
    
    return Response({
        'consultations': [{'id': c.id, 'type': 'consultation', 'nutritionist_name': c.nutritionist.get_full_name() or c.nutritionist.email.split('@')[0], 'date': c.date.isoformat(), 'zoom_link': c.zoom_link} for c in consultations],
        'meals': [{'type': 'meal', 'date': date, 'meals': meals_list} for date, meals_list in meals_by_date.items()]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_diet_plan(request):
    from nutritionists.models import DietPlan
    plan = DietPlan.objects.filter(patient=request.user, is_active=True).first()
    if not plan:
        return Response({'has_plan': False, 'message': 'No active diet plan'})
    
    meals_by_type = {}
    for meal in plan.meals.all():
        if meal.meal_type not in meals_by_type:
            meals_by_type[meal.meal_type] = []
        meals_by_type[meal.meal_type].append({'id': meal.id, 'food_name': meal.food_name, 'quantity': meal.quantity, 'calories': meal.calories, 'meal_type': meal.meal_type})
    
    return Response({'has_plan': True, 'plan': {'id': plan.id, 'name': plan.name, 'description': plan.description, 'start_date': plan.start_date, 'end_date': plan.end_date, 'nutritionist': plan.nutritionist.get_full_name(), 'meals': meals_by_type}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_today_meals_checklist(request):
    from nutritionists.models import PatientMealChecklist
    from django.utils import timezone
    today = timezone.now().date()
    meals = PatientMealChecklist.objects.filter(patient=request.user, date=today).order_by('meal_time')
    return Response({'date': today, 'meals': [{'id': m.id, 'name': m.meal_name, 'status': m.status, 'meal_time': m.meal_time} for m in meals], 'completed_count': meals.filter(status='completed').count(), 'total_count': meals.count()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_meal_checklist(request, checklist_id):
    from nutritionists.models import PatientMealChecklist
    from django.utils import timezone
    try:
        checklist = PatientMealChecklist.objects.get(id=checklist_id, patient=request.user)
        checklist.status = 'completed'
        checklist.completed_at = timezone.now()
        checklist.save()
        
        today = timezone.now().date()
        all_meals = PatientMealChecklist.objects.filter(patient=request.user, date=today)
        completed = all_meals.filter(status='completed').count()
        
        if completed == all_meals.count() and all_meals.count() > 0:
            # ✅ CORRECTION
            profile = request.user.profile
            from datetime import date, timedelta
            if profile.last_streak_date == today - timedelta(days=1):
                profile.nutrition_streak += 1
            elif profile.last_streak_date != today:
                profile.nutrition_streak = 1
            profile.last_streak_date = today
            profile.save()
        
        return Response({'status': 'completed', 'message': 'Meal marked as completed'})
    except PatientMealChecklist.DoesNotExist:
        return Response({'error': 'Meal not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_payment(request):
    from django.utils import timezone
    from nutritionists.models import DietPlan, Meal, PatientSubscription, PatientMealChecklist, Notification
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    plan_name = request.data.get('plan_name', '30-Day Metabolic Weight Loss')
    amount = request.data.get('amount', 49.99)
    duration_months = request.data.get('duration_months', 1)
    plan_type = request.data.get('plan_type', 'standard')
    package_type = request.data.get('package_type', 'standard_simple')
    bonus_ai = request.data.get('bonus_ai')
    bonus_consultation = request.data.get('bonus_consultation')
    
    # Déterminer les fonctionnalités activées
    has_ai = (plan_type == 'premium') or (bonus_ai and bonus_ai.get('active'))
    has_consultations = (plan_type == 'premium') or (bonus_consultation and bonus_consultation.get('active'))
    
    # Mettre à jour le profil
    from users.models import UserProfile
    UserProfile.objects.filter(user=request.user).update(
        subscription_plan='premium' if plan_type == 'premium' else 'standard',
        payment_completed=True,
        payment_date=timezone.now(),
        has_diet_plan=True,
        has_ai_tracker=has_ai,
        has_consultations=has_consultations
    )
    
    # Créer l'abonnement
    subscription = PatientSubscription.objects.create(
        patient=request.user,
        plan_name=plan_name,
        plan_type=plan_type,
        price_paid=amount,
        duration_months=duration_months,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timezone.timedelta(days=duration_months * 30),
        status='active'
    )
    
    # ========== CRÉER LE DIET PLAN POUR L'UTILISATEUR ==========
    # Récupérer un nutritionniste (admin par défaut)
    default_nutritionist = User.objects.filter(
        profile__role='nutritionist',
        is_active=True
    ).first()
    
    if not default_nutritionist:
        default_nutritionist = User.objects.filter(is_superuser=True).first()
    
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=duration_months * 30)
    
    # Créer le plan diététique avec le nom choisi par l'utilisateur
    diet_plan = DietPlan.objects.create(
        nutritionist=default_nutritionist,
        patient=request.user,
        name=plan_name,
        description=f"Votre plan {plan_name} - {duration_months} mois",
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    
    # Définir les repas en fonction du plan choisi
    meals_to_add = []
    
    if "weight loss" in plan_name.lower() or "metabolic" in plan_name.lower():
        meals_to_add = [
            {'meal_type': 'breakfast', 'food_name': 'Omelette aux légumes', 'calories': 350, 'quantity': '1 portion'},
            {'meal_type': 'breakfast', 'food_name': 'Thé vert sans sucre', 'calories': 0, 'quantity': '1 tasse'},
            {'meal_type': 'lunch', 'food_name': 'Poulet grillé avec quinoa', 'calories': 550, 'quantity': '1 assiette'},
            {'meal_type': 'lunch', 'food_name': 'Salade verte', 'calories': 50, 'quantity': '1 assiette'},
            {'meal_type': 'snack', 'food_name': 'Pomme', 'calories': 80, 'quantity': '1 fruit'},
            {'meal_type': 'snack', 'food_name': 'Amandes', 'calories': 100, 'quantity': '1 poignée'},
            {'meal_type': 'dinner', 'food_name': 'Saumon avec légumes', 'calories': 500, 'quantity': '1 assiette'},
            {'meal_type': 'dinner', 'food_name': 'Soupe de légumes', 'calories': 80, 'quantity': '1 bol'},
        ]
    elif "muscle" in plan_name.lower() or "builder" in plan_name.lower():
        meals_to_add = [
            {'meal_type': 'breakfast', 'food_name': 'Porridge protéiné', 'calories': 500, 'quantity': '1 bol'},
            {'meal_type': 'breakfast', 'food_name': 'Oeufs brouillés', 'calories': 240, 'quantity': '3 oeufs'},
            {'meal_type': 'lunch', 'food_name': 'Poulet avec riz complet', 'calories': 650, 'quantity': '1 assiette'},
            {'meal_type': 'lunch', 'food_name': 'Avocat', 'calories': 160, 'quantity': '1/2'},
            {'meal_type': 'snack', 'food_name': 'Yaourt grec', 'calories': 180, 'quantity': '1 pot'},
            {'meal_type': 'snack', 'food_name': 'Barre protéinée', 'calories': 200, 'quantity': '1 barre'},
            {'meal_type': 'dinner', 'food_name': 'Steak de boeuf', 'calories': 600, 'quantity': '1 assiette'},
            {'meal_type': 'dinner', 'food_name': 'Légumes verts', 'calories': 80, 'quantity': '1 portion'},
        ]
    else:
        # Plan équilibré standard
        meals_to_add = [
            {'meal_type': 'breakfast', 'food_name': 'Céréales complètes', 'calories': 400, 'quantity': '1 bol'},
            {'meal_type': 'breakfast', 'food_name': 'Jus d\'orange', 'calories': 110, 'quantity': '1 verre'},
            {'meal_type': 'lunch', 'food_name': 'Pâtes complètes', 'calories': 550, 'quantity': '1 assiette'},
            {'meal_type': 'lunch', 'food_name': 'Salade verte', 'calories': 50, 'quantity': '1 assiette'},
            {'meal_type': 'snack', 'food_name': 'Compote', 'calories': 70, 'quantity': '1 pot'},
            {'meal_type': 'snack', 'food_name': 'Fruits secs', 'calories': 120, 'quantity': '1 poignée'},
            {'meal_type': 'dinner', 'food_name': 'Dinde avec légumes', 'calories': 480, 'quantity': '1 assiette'},
            {'meal_type': 'dinner', 'food_name': 'Quinoa', 'calories': 150, 'quantity': '1 portion'},
        ]
    
    # Ajouter tous les repas au plan
    for meal_data in meals_to_add:
        Meal.objects.create(
            plan=diet_plan,
            meal_type=meal_data['meal_type'],
            food_name=meal_data['food_name'],
            quantity=meal_data['quantity'],
            calories=meal_data['calories']
        )
    
    # Générer la checklist des repas pour chaque jour de la période
    meal_time_map = {
        'breakfast': '08:00',
        'lunch': '12:30',
        'snack': '16:00',
        'dinner': '19:30'
    }
    
    current_date = start_date
    while current_date <= end_date:
        for meal in diet_plan.meals.all():
            meal_type_display = dict(Meal.MEAL_TYPES).get(meal.meal_type, meal.meal_type)
            meal_name_display = f"{meal_type_display}: {meal.food_name}"
            meal_time = meal_time_map.get(meal.meal_type, '12:00')
            
            PatientMealChecklist.objects.update_or_create(
                patient=request.user,
                meal=meal,
                date=current_date,
                defaults={
                    'meal_name': meal_name_display,
                    'meal_time': meal_time,
                    'calories': meal.calories,
                    'status': 'pending'
                }
            )
        current_date += timedelta(days=1)
    
    # Notification pour informer l'utilisateur
    Notification.objects.create(
        user=request.user,
        notification_type='plan_updated',
        title='🎉 Votre plan nutritionnel est prêt !',
        message=f'Votre plan "{diet_plan.name}" a été activé. Rendez-vous dans "Diet Plans" pour voir vos repas.',
        related_id=diet_plan.id,
        is_read=False
    )
    
    return Response({
        'success': True,
        'message': 'Payment successful! Your diet plan has been activated.',
        'has_ai': has_ai,
        'has_consultations': has_consultations,
        'diet_plan_created': True,
        'subscription': {
            'plan_type': plan_type,
            'plan_name': plan_name,
            'has_ai': has_ai,
            'has_consultations': has_consultations
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoices(request):
    from nutritionists.models import PatientSubscription
    subscriptions = PatientSubscription.objects.filter(patient=request.user).order_by('-created_at')
    total_spent = sum(float(s.price_paid) for s in subscriptions)
    last_payment = subscriptions.first()
    return Response({
        'subscriptions': [{'id': s.id, 'plan_name': s.plan_name, 'amount': float(s.price_paid), 'duration_months': s.duration_months, 'start_date': s.start_date.isoformat(), 'end_date': s.end_date.isoformat(), 'status': s.status, 'is_active': s.is_active, 'days_left': s.days_left, 'created_at': s.created_at.isoformat(), 'payment_date': s.created_at.strftime('%d %B %Y'), 'expiry_date': s.end_date.strftime('%d %B %Y')} for s in subscriptions],
        'summary': {'total_spent': total_spent, 'active_subscriptions': sum(1 for s in subscriptions if s.is_active), 'total_subscriptions': subscriptions.count(), 'last_payment': {'date': last_payment.created_at.strftime('%d %B %Y') if last_payment else None, 'amount': float(last_payment.price_paid) if last_payment else None, 'plan': last_payment.plan_name if last_payment else None} if last_payment else None}
    })

from .models import Message
from django.db.models import Q

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """Récupérer toutes les conversations de l'utilisateur"""
    user = request.user
    
    conversations = []
    user_ids = set()
    
    # Pour l'admin: voir TOUS les utilisateurs
    if user.is_superuser:
        # Récupérer tous les utilisateurs (patients et nutritionnistes)
        all_users = User.objects.exclude(id=user.id).filter(is_active=True)
        for other_user in all_users:
            user_ids.add(other_user.id)
    
    # Pour les patients: voir leur nutritionniste ET l'admin
    elif user.profile.role == 'client':
        # Ajouter l'admin
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            user_ids.add(admin.id)
        
        # Ajouter le nutritionniste assigné
        from nutritionists.models import PatientAssignment
        assignment = PatientAssignment.objects.filter(patient=user, is_active=True).first()
        if assignment and assignment.nutritionist:
            user_ids.add(assignment.nutritionist.id)
    
    # Pour les nutritionnistes: voir leurs patients ET l'admin
    elif user.profile.role == 'nutritionist':
        # Ajouter l'admin
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            user_ids.add(admin.id)
        
        # Ajouter les patients assignés
        from nutritionists.models import PatientAssignment
        assignments = PatientAssignment.objects.filter(nutritionist=user, is_active=True)
        for assignment in assignments:
            if assignment.patient:
                user_ids.add(assignment.patient.id)
    
    
    for other_id in user_ids:
        try:
            other = User.objects.get(id=other_id)
            
         
            last_message = Message.objects.filter(
                Q(sender=user, receiver=other) | Q(sender=other, receiver=user)
            ).order_by('-created_at').first()
            
            
            unread_count = Message.objects.filter(
                sender=other, receiver=user, is_read=False
            ).count()
            
            conversations.append({
                'user_id': other.id,
                'name': other.get_full_name() or other.email.split('@')[0],
                'email': other.email,
                'role': 'admin' if other.is_superuser else other.profile.role,
                'last_message': last_message.content if last_message else 'No messages yet',
                'last_message_time': last_message.created_at.isoformat() if last_message else None,
                'unread_count': unread_count
            })
        except User.DoesNotExist:
            continue
    
    return Response(conversations)

from nutritionists.models import DietPlan, Meal
def generate_meal_checklist_for_plan(plan):
    """Génère la checklist des repas pour tous les jours du plan"""
    from nutritionists.models import PatientMealChecklist
    from datetime import timedelta
    
    meal_time_map = {
        'breakfast': '08:00',
        'lunch': '12:30',
        'snack': '16:00',
        'dinner': '19:30'
    }
    
    start_date = plan.start_date
    end_date = plan.end_date if plan.end_date else start_date + timedelta(days=30)
    
    current_date = start_date
    while current_date <= end_date:
        for meal in plan.meals.all():
            meal_type_display = dict(Meal.MEAL_TYPES).get(meal.meal_type, meal.meal_type)
            meal_name = f"{meal_type_display}: {meal.food_name}"
            meal_time = meal_time_map.get(meal.meal_type, '12:00')
            
            PatientMealChecklist.objects.get_or_create(
                patient=plan.patient,
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_plan(request):
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        subscription_plan = getattr(profile, 'subscription_plan', 'free')
        payment_completed = getattr(profile, 'payment_completed', False)
        
         
        has_ai = getattr(profile, 'has_ai_tracker', False)
        has_consultations = getattr(profile, 'has_consultations', False)
       
        if subscription_plan == 'premium':
            has_ai = True
            has_consultations = True
    else:
        subscription_plan = 'free'
        payment_completed = False
        has_ai = False
        has_consultations = False
    
    return Response({
        'subscription_plan': subscription_plan,
        'payment_completed': payment_completed,
        'has_consultations': has_consultations, 
        'has_messages': has_consultations,        
        'has_diet_plan': subscription_plan in ['standard', 'premium'] or has_ai or has_consultations,
        'has_ai': has_ai,                        
        'has_progress': has_ai or has_consultations
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    """Récupérer les messages entre l'utilisateur courant et un autre utilisateur"""
    user = request.user
    
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    # Récupérer tous les messages entre les deux utilisateurs
    messages = Message.objects.filter(
        Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
    ).order_by('created_at')
    
    # Marquer les messages reçus comme lus
    Message.objects.filter(sender=other_user, receiver=user, is_read=False).update(is_read=True)
    
    # Formater les messages
    result = []
    for msg in messages:
        is_mine = msg.sender.id == user.id
        result.append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_name': msg.sender.get_full_name() or msg.sender.email.split('@')[0],
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'time_display': msg.created_at.strftime('%H:%M'),
            'is_mine': is_mine
        })
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Envoyer un message à un autre utilisateur"""
    receiver_id = request.data.get('receiver_id')
    content = request.data.get('content', '').strip()
    
    if not receiver_id or not content:
        return Response({'error': 'Missing receiver_id or content'}, status=400)
    
    try:
        receiver = User.objects.get(id=receiver_id)
    except User.DoesNotExist:
        return Response({'error': 'Receiver not found'}, status=404)
    
    # Créer le message
    message = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        content=content
    )
    
    # Créer une notification pour le destinataire
    try:
        from nutritionists.models import Notification
        Notification.objects.create(
            user=receiver,
            notification_type='new_message',
            title=f'💬 New message from {request.user.get_full_name() or request.user.email}',
            message=f'{content[:50]}{"..." if len(content) > 50 else ""}',
            related_id=message.id,
            is_read=False
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    return Response({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'time_display': message.created_at.strftime('%H:%M'),
            'is_mine': True
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_user(request):
    """Récupérer l'utilisateur admin (superuser)"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        return Response({
            'id': admin.id,
            'name': admin.get_full_name() or admin.email.split('@')[0],
            'email': admin.email
        })
    return Response({'error': 'No admin found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_nutritionist(request):
    try:
        user = request.user
        print(f"User: {user.email}, profile role: {user.profile.role}")
        
        if user.profile.role != 'client':
            return Response({'error': 'Only patients can access this'}, status=403)
        
        from nutritionists.models import PatientAssignment
        assignment = PatientAssignment.objects.filter(patient=user, is_active=True).select_related('nutritionist').first()
        
        if not assignment or not assignment.nutritionist:
            return Response({'error': 'No nutritionist assigned'}, status=404)
        
        nutritionist = assignment.nutritionist
        return Response({
            'id': nutritionist.id, 
            'name': nutritionist.get_full_name() or nutritionist.email.split('@')[0], 
            'email': nutritionist.email
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_nutritionist(request):
    from nutritionists.models import AssignmentRequest, PatientAssignment, Notification
    from accounts.models import CustomUser
    from users.models import UserProfile
    
    nutritionist_id = request.data.get('nutritionist_id')
    if not nutritionist_id:
        return Response({'error': 'Nutritionist ID required'}, status=400)
    
    # ✅ Correction : utiliser profile.role
    if request.user.profile.role != 'client':
        return Response({'error': 'Only patients can request a nutritionist'}, status=403)
    
    try:
        nutritionist = CustomUser.objects.get(id=nutritionist_id)
        # Vérifier que l'utilisateur est bien un nutritionniste
        if nutritionist.profile.role != 'nutritionist':
            return Response({'error': 'User is not a nutritionist'}, status=400)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Nutritionist not found'}, status=404)
    except AttributeError:
        return Response({'error': 'Nutritionist profile not found'}, status=400)
    
    existing_request = AssignmentRequest.objects.filter(patient=request.user, nutritionist=nutritionist, status='pending').first()
    if existing_request:
        return Response({'success': True, 'message': 'Your request is already pending.', 'already_pending': True, 'redirect': '/user-profile/'})
    
    existing_assign = PatientAssignment.objects.filter(patient=request.user, nutritionist=nutritionist, is_active=True).first()
    if existing_assign:
       
        nut_name = f"{nutritionist.first_name} {nutritionist.last_name}".strip() or nutritionist.email.split('@')[0]
        return Response({'success': True, 'message': f'You are already assigned to {nut_name}.', 'already_assigned': True, 'redirect': '/user-profile/'})
    
    assignment_request = AssignmentRequest.objects.create(patient=request.user, nutritionist=nutritionist, status='pending')
    
    
    user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email.split('@')[0]
    nut_name = f"{nutritionist.first_name} {nutritionist.last_name}".strip() or nutritionist.email.split('@')[0]
    
    # Créer une notification pour l'admin
    Notification.objects.create(
        nutritionist=None, 
        notification_type='assignment_request', 
        title='🔔 New Assignment Request', 
        message=f'{user_name} wants to be assigned to {nut_name}.', 
        related_patient=request.user, 
        related_id=assignment_request.id, 
        is_read=False, 
        is_admin_notification=True
    )
    
    return Response({
        'success': True, 
        'message': 'Your request has been sent to admin. You will be notified once approved.', 
        'request_id': assignment_request.id, 
        'redirect': '/user-profile/'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_diet_plans(request):
    """Récupérer tous les plans diététiques du patient"""
    from nutritionists.models import DietPlan
    
    plans = DietPlan.objects.filter(patient=request.user).order_by('-created_at')
    
    result = []
    for plan in plans:
        meals_list = []
        for meal in plan.meals.all():
            meals_list.append({
                'id': meal.id,
                'food_name': meal.food_name,
                'meal_type': meal.meal_type,
                'calories': meal.calories,
                'quantity': meal.quantity
            })
        
        result.append({
            'id': plan.id,
            'plan_name': plan.name,
            'description': plan.description,
            'nutritionist_name': plan.nutritionist.get_full_name(),
            'start_date': plan.start_date.isoformat() if plan.start_date else None,
            'end_date': plan.end_date.isoformat() if plan.end_date else None,
            'status': 'active' if plan.is_active else 'completed',
            'created_at': plan.created_at.isoformat(),
            'meals': meals_list
        })
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_notifications(request):
    """Récupérer les notifications du patient"""
    from nutritionists.models import Notification
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    def get_time_ago(dt):
        from django.utils import timezone
        now = timezone.now()
        diff = now - dt
        if diff.days > 0:
            return f'{diff.days} days ago'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} hours ago'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60} minutes ago'
        return 'Just now'
    
    return Response({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'time_ago': get_time_ago(n.created_at)
        } for n in notifications[:20]],
        'unread_count': unread_count
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    from nutritionists.models import Notification
    
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Marquer toutes les notifications du patient comme lues"""
    from nutritionists.models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'success': True})

from datetime import datetime

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_meal_checklist(request):
    """Ajouter un repas à la checklist du patient pour une date donnée"""
    from nutritionists.models import PatientMealChecklist
    
    data = request.data
    meal_name = data.get('meal_name')
    meal_type = data.get('meal_type')
    calories = data.get('calories', 0)
    meal_time = data.get('meal_time', '12:00')
    date_str = data.get('date')
    
    if not meal_name or not date_str:
        return Response({'error': 'meal_name and date required'}, status=400)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        target_date = timezone.now().date()
    
    # Créer le repas dans la checklist
    checklist, created = PatientMealChecklist.objects.get_or_create(
        patient=request.user,
        meal_name=meal_name,
        date=target_date,
        defaults={
            'meal_time': meal_time,
            'calories': calories,
            'status': 'pending'
        }
    )
    
    if not created and checklist.status == 'pending':
        # Mettre à jour si nécessaire
        checklist.meal_time = meal_time
        checklist.calories = calories
        checklist.save()
    
    return Response({
        'success': True,
        'message': 'Meal added to checklist',
        'created': created,
        'checklist_id': checklist.id
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_subscription(request):
    from nutritionists.models import PatientSubscription
    from django.utils import timezone
    
    today = timezone.now().date()
    
    subscription = PatientSubscription.objects.filter(
        patient=request.user,
        status='active',
        end_date__gte=today
    ).first()
    
    if not subscription:
        return Response({
            'has_active_subscription': False,
            'is_expired': True,
            'subscription': None
        })
    
    days_left = (subscription.end_date - today).days
    
    # ✅ Récupérer les bonus depuis le profil utilisateur
    profile = request.user.profile
    has_ai = getattr(profile, 'has_ai_tracker', False)
    has_consultations = getattr(profile, 'has_consultations', False)
    
    # ✅ Vérifier aussi dans les champs bonus du subscription si existent
    # (si vous avez ajouté ces champs dans PatientSubscription)
    if hasattr(subscription, 'bonus_ai'):
        has_ai = subscription.bonus_ai or has_ai
    if hasattr(subscription, 'bonus_consultation'):
        has_consultations = subscription.bonus_consultation or has_consultations
    
    return Response({
        'has_active_subscription': True,
        'is_expired': False,
        'subscription': {
            'id': subscription.id,
            'plan_name': subscription.plan_name,
            'plan_type': getattr(subscription, 'plan_type', 'standard'),
            'amount': float(subscription.price_paid),
            'duration_months': subscription.duration_months,
            'start_date': subscription.start_date.isoformat(),
            'end_date': subscription.end_date.isoformat(),
            'days_left': days_left,
            'is_active': subscription.is_active,
            'has_ai': has_ai,                    # ✅ NOUVEAU
            'has_consultations': has_consultations  # ✅ NOUVEAU
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoices(request):
    """Récupérer l'historique des paiements du patient"""
    from nutritionists.models import PatientSubscription
    
    subscriptions = PatientSubscription.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    return Response({
        'subscriptions': [{
            'id': s.id,
            'plan_name': s.plan_name,
            'amount': float(s.price_paid),
            'duration_months': s.duration_months,
            'start_date': s.start_date.isoformat(),
            'end_date': s.end_date.isoformat(),
            'payment_date': s.created_at.isoformat(),
            'expiry_date': s.end_date.isoformat(),
            'is_active': s.is_active,
            'status': s.status
        } for s in subscriptions],
        'summary': {
            'total_spent': sum(float(s.price_paid) for s in subscriptions),
            'total_subscriptions': subscriptions.count(),
            'active_count': subscriptions.filter(status='active').count()
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, invoice_id):
    """Télécharger une facture PDF"""
    from nutritionists.models import PatientSubscription
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from io import BytesIO
    from django.http import HttpResponse
    
    try:
        subscription = PatientSubscription.objects.get(id=invoice_id, patient=request.user)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#27AE60'),
            alignment=1
        )
        
        story = []
        story.append(Paragraph("NutriLife", title_style))
        story.append(Paragraph("Invoice", styles['Heading2']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Invoice ID:</b> INV-{subscription.id}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {subscription.created_at.strftime('%d %B %Y')}", styles['Normal']))
        story.append(Paragraph(f"<b>Patient:</b> {request.user.get_full_name() or request.user.email}", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>Subscription Details</b>", styles['Heading3']))
        story.append(Paragraph(f"<b>Plan:</b> {subscription.plan_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Duration:</b> {subscription.duration_months} month(s)", styles['Normal']))
        story.append(Paragraph(f"<b>Start Date:</b> {subscription.start_date.strftime('%d %B %Y')}", styles['Normal']))
        story.append(Paragraph(f"<b>End Date:</b> {subscription.end_date.strftime('%d %B %Y')}", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Total Amount:</b> ${float(subscription.price_paid):.2f}", styles['Normal']))
        story.append(Spacer(1, 30))
        story.append(Paragraph("Thank you for choosing NutriLife!", styles['Italic']))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{subscription.id}.pdf"'
        return response
        
    except PatientSubscription.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=404)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_diet_plan_pdf(request, plan_id):
    """Télécharger un plan diététique en PDF"""
    from nutritionists.models import DietPlan
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from io import BytesIO
    from django.http import HttpResponse
    from datetime import datetime
    
    try:
        # Récupérer le plan
        plan = DietPlan.objects.get(id=plan_id, patient=request.user)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                topMargin=2*cm, bottomMargin=2*cm,
                                leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#27AE60'),
            alignment=1,  # Center
            spaceAfter=20
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#FF7A00'),
            alignment=1,
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=12,
            spaceAfter=8
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        story = []
        
        # En-tête
        story.append(Paragraph("NutriLife", title_style))
        story.append(Paragraph("Plan Diététique Personnalisé", subtitle_style))
        story.append(Spacer(1, 10))
        
        # Date
        story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", normal_style))
        story.append(Spacer(1, 15))
        
        # Informations patient
        patient_name = request.user.get_full_name() or request.user.email
        story.append(Paragraph(f"<b>Patient:</b> {patient_name}", normal_style))
        story.append(Spacer(1, 20))
        
        # Détails du plan
        story.append(Paragraph(f"<b>Plan:</b> {plan.name}", section_style))
        if plan.description:
            story.append(Paragraph(plan.description.replace('\n', '<br/>'), normal_style))
        story.append(Spacer(1, 10))
        
        # Dates
        story.append(Paragraph(f"<b>Date de début:</b> {plan.start_date.strftime('%d %B %Y') if plan.start_date else 'Non définie'}", normal_style))
        if plan.end_date:
            story.append(Paragraph(f"<b>Date de fin:</b> {plan.end_date.strftime('%d %B %Y')}", normal_style))
        story.append(Spacer(1, 15))
        
        # Programme alimentaire par type de repas
        story.append(Paragraph("Programme Alimentaire", section_style))
        
        meals_by_type = {'breakfast': [], 'lunch': [], 'snack': [], 'dinner': []}
        for meal in plan.meals.all():
            if meal.meal_type in meals_by_type:
                meals_by_type[meal.meal_type].append(meal)
        
        meal_labels = {
            'breakfast': '🍳 Petit-déjeuner',
            'lunch': '🥗 Déjeuner', 
            'snack': '🍎 Collation',
            'dinner': '🌙 Dîner'
        }
        
        for meal_type, meals in meals_by_type.items():
            if meals:
                story.append(Paragraph(f"<b>{meal_labels.get(meal_type, meal_type)}</b>", styles['Heading4']))
                story.append(Spacer(1, 5))
                
                # Créer un tableau pour les repas
                table_data = [['Aliment', 'Quantité', 'Calories']]
                for meal in meals:
                    table_data.append([
                        meal.food_name,
                        meal.quantity or '1 portion',
                        f"{meal.calories or 0} kcal"
                    ])
                
                table = Table(table_data, colWidths=[8*cm, 4*cm, 3*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 15))
        
        # Total calories par jour
        total_calories = sum(meal.calories or 0 for meal in plan.meals.all())
        story.append(Paragraph(f"<b>Total calories estimées par jour:</b> {total_calories} kcal", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Pied de page
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#27AE60'), spaceBefore=20, spaceAfter=10))
        story.append(Paragraph("Merci de faire confiance à NutriLife pour votre parcours santé !", styles['Italic']))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="diet_plan_{plan.id}_{datetime.now().strftime("%Y%m%d")}.pdf"'
        return response
        
    except DietPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)