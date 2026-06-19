from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from users.models import UserProfile
from nutritionists.models import PatientAssignment, Notification, SpecialOffer, PatientSubscription, AssignmentRequest
from consultations.models import NutritionistProfile, Consultation
from django.utils import timezone
from datetime import datetime, timedelta
from users.models import FoodLog, WeightHistory

User = get_user_model()

def get_time_ago(dt):
    if not dt:
        return 'Just now'
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    users = User.objects.filter(profile__role='client').order_by('-date_joined')
    
    users_data = []
    for user in users:
        profile = getattr(user, 'profile', None)
        # Récupérer la demande d'assignation en attente
        pending_request = AssignmentRequest.objects.filter(patient=user, status='pending').first()
        # Récupérer l'assignation active (nutritionniste déjà assigné)
        active_assignment = PatientAssignment.objects.filter(patient=user, is_active=True).first()
        # Récupérer l'abonnement actif
        active_subscription = PatientSubscription.objects.filter(patient=user, status='active').first()
        
        # Déterminer le plan
        subscription_plan = 'Standard'
        if active_subscription:
            subscription_plan = active_subscription.plan_name
        elif profile and profile.subscription_plan:
            subscription_plan = profile.subscription_plan.capitalize()
        
        users_data.append({
            'id': user.id,
            'name': user.get_full_name() or user.email.split('@')[0],
            'email': user.email,
            'status': 'Active' if user.is_active else 'Blocked',
            'weight': profile.weight if profile else None,
            'goal_weight': profile.goal if profile else None,
            'height': profile.height if profile else None,
            'health_conditions': profile.health_conditions if profile else [],
            'subscription_plan': subscription_plan,
            'created_at': user.date_joined.isoformat() if user.date_joined else None,
            'payment_completed': profile.payment_completed if profile else False,
            'payment_date': profile.payment_date.isoformat() if profile and profile.payment_date else None,
            'assignment_request_id': pending_request.id if pending_request else None,
            'requested_nutritionist': pending_request.nutritionist.get_full_name() if pending_request and pending_request.nutritionist else None,
            'assignment_status': 'pending' if pending_request else ('assigned' if active_assignment else 'none'),
            'assigned_nutritionist': active_assignment.nutritionist.get_full_name() if active_assignment and active_assignment.nutritionist else None
        })
    return Response(users_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionists_list(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
  
    nutritionists = User.objects.filter(profile__role='nutritionist')
    return Response([{'id': n.id, 'name': n.get_full_name() or n.email.split('@')[0], 'email': n.email} for n in nutritionists])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_patient_to_nutritionist(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    patient_id = request.data.get('patient_id')
    nutritionist_id = request.data.get('nutritionist_id')
    if not patient_id or not nutritionist_id:
        return Response({'error': 'Patient and nutritionist required'}, status=400)
    try:
        patient = User.objects.get(id=patient_id, role='patient')
        nutritionist = User.objects.get(id=nutritionist_id, role='nutritionist')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    assignment, created = PatientAssignment.objects.get_or_create(patient=patient, nutritionist=nutritionist, defaults={'is_active': True})
    if not created and not assignment.is_active:
        assignment.is_active = True
        assignment.save()
    Notification.objects.create(nutritionist=nutritionist, notification_type='patient_assigned', title='New Patient Assigned 🎉', message=f'{patient.get_full_name()} has been assigned to you. Check your patient list!', related_patient=patient)
    return Response({'message': f'Patient {patient.email} assigned to {nutritionist.email}'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_user(request, user_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    try:
        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        return Response({'message': f'User {user.email} {"blocked" if not user.is_active else "activated"}'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_patient(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    data = request.data
    if User.objects.filter(email=data['email']).exists():
        return Response({'error': 'Email already exists'}, status=400)
    patient = User.objects.create_user(email=data['email'], password=data['password'], first_name=data.get('first_name', ''), last_name=data.get('last_name', ''), role='patient')
    UserProfile.objects.create(user=patient, weight=data.get('weight', 0), height=data.get('height', 0), goal=data.get('goal_weight'), health_conditions=data.get('health_conditions', []))
    return Response({'message': f'Patient {patient.email} created successfully', 'patient_id': patient.id}, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_nutritionists(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
   
    nutritionists = User.objects.filter(profile__role='nutritionist').order_by('-date_joined')
    nutritionists_data = []
    for nutritionist in nutritionists:
        try:
            profile = NutritionistProfile.objects.get(user=nutritionist)
            specialization = profile.specialization if profile.specialization else 'Not specified'
        except NutritionistProfile.DoesNotExist:
            specialization = 'No profile'
        patients_count = PatientAssignment.objects.filter(nutritionist=nutritionist, is_active=True).count()
        nutritionists_data.append({
            'id': nutritionist.id,
            'name': nutritionist.get_full_name() or nutritionist.email.split('@')[0],
            'email': nutritionist.email,
            'specialization': specialization,
            'patients_count': patients_count,
            'status': 'Active' if nutritionist.is_active else 'Inactive'
        })
    return Response(nutritionists_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_nutritionist(request):
    if not request.user.is_superuser:
        print("✅ VERSION CORRIGÉE DE create_nutritionist - Utilise User")
        return Response({'error': 'Admin access required'}, status=403)
    
    data = request.data
    email = data.get('email')
    
    # Vérifier si l'email existe déjà
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=400)
    
    try:
        # Créer l'utilisateur nutritionniste
        nutritionist = User.objects.create_user(
            email=email,
            password=data.get('password'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_staff=True
        )
        
        # Créer le profil UserProfile
        profile, created = UserProfile.objects.get_or_create(user=nutritionist)
        profile.role = 'nutritionist'
        profile.save()
        
        # Créer le profil NutritionistProfile
        nutritionist_profile = NutritionistProfile.objects.create(
            user=nutritionist,
            specialization=data.get('specialization', ''),
            bio=data.get('bio', ''),
            experience_years=data.get('experience_years', 0),
            is_available=data.get('is_available', True)
        )
        
        return Response({
            'message': f'Nutritionist {nutritionist.email} created successfully',
            'nutritionist_id': nutritionist.id
        }, status=201)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=400)
    
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_nutritionist_status(request, nutritionist_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    try:
        nutritionist = User.objects.get(id=nutritionist_id, role='nutritionist')
    except User.DoesNotExist:
        return Response({'error': 'Nutritionist not found'}, status=404)
    is_active = request.data.get('is_active')
    nutritionist.is_active = is_active
    nutritionist.save()
    try:
        profile = NutritionistProfile.objects.get(user=nutritionist)
        profile.is_available = is_active
        profile.save()
    except NutritionistProfile.DoesNotExist:
        pass
    return Response({'message': f'Nutritionist {nutritionist.email} {"activated" if is_active else "deactivated"}'})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_nutritionist(request, nutritionist_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    try:
        nutritionist = User.objects.get(id=nutritionist_id, role='nutritionist')
        email = nutritionist.email
        nutritionist.delete()
        return Response({'message': f'Nutritionist {email} deleted'})
    except User.DoesNotExist:
        return Response({'error': 'Nutritionist not found'}, status=404)

from django.db.models import Sum

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_stats(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    today = datetime.now().date()
    start_of_quarter = datetime(today.year, ((today.month - 1) // 3) * 3 + 1, 1).date()
    
    # Consultations du trimestre
    total_consultations = Consultation.objects.filter(
        date__date__gte=start_of_quarter, 
        status='completed'
    ).count()
    
    # Repas analysés par IA
    total_meals_analyzed = FoodLog.objects.count()
    
    # Progrès moyen des patients
    profiles = UserProfile.objects.filter(role='client')
    total_progress = 0
    patient_count = 0
    for profile in profiles:
        if profile.weight and profile.goal and profile.weight > 0:
            first_weight = WeightHistory.objects.filter(user=profile.user).order_by('date').first()
            if first_weight:
                initial_weight = first_weight.weight_kg
                current_weight = profile.weight
                goal_weight = profile.goal
                if goal_weight < initial_weight:
                    total_to_lose = initial_weight - goal_weight
                    lost_so_far = initial_weight - current_weight
                    if total_to_lose > 0:
                        progress = min(100, max(0, (lost_so_far / total_to_lose) * 100))
                        total_progress += progress
                        patient_count += 1
                elif goal_weight > initial_weight:
                    total_to_gain = goal_weight - initial_weight
                    gained_so_far = current_weight - initial_weight
                    if total_to_gain > 0:
                        progress = min(100, max(0, (gained_so_far / total_to_gain) * 100))
                        total_progress += progress
                        patient_count += 1
    
    avg_user_progress = round(total_progress / patient_count) if patient_count > 0 else 0
    
  
    monthly_revenue = []
    for month in range(1, 13):
        revenue = PatientSubscription.objects.filter(
            created_at__year=today.year,
            created_at__month=month,
            status='active'
        ).aggregate(total=Sum('price_paid'))['total'] or 0
        monthly_revenue.append({
            'month': datetime(today.year, month, 1).strftime('%b'),
            'revenue': float(revenue)
        })
    
   
    subscriptions = PatientSubscription.objects.filter(status='active')
    plan_distribution = {}
    for sub in subscriptions:
        plan_name = sub.plan_name
        plan_distribution[plan_name] = plan_distribution.get(plan_name, 0) + 1
    
    # Si pas de données, valeurs par défaut
    if not plan_distribution:
        plan_distribution = {'No active plans': 0}
    
    # Statistiques de base
    active_nutritionists = User.objects.filter(profile__role='nutritionist', is_active=True).count()
    active_patients = User.objects.filter(profile__role='client', is_active=True).count()
    active_subscriptions = PatientSubscription.objects.filter(status='active').count()
    
    return Response({
        'total_consultations': total_consultations,
        'ai_track_usage': total_meals_analyzed,
        'avg_user_progress': avg_user_progress,
        'monthly_revenue': monthly_revenue,
        'plan_distribution': plan_distribution,
        'active_nutritionists': active_nutritionists,
        'active_patients': active_patients,
        'active_subscriptions': active_subscriptions
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_requests(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    trials = Consultation.objects.filter(is_trial=True).order_by('-created_at').select_related('patient', 'nutritionist')
    return Response([{'id': t.id, 'patient_name': t.patient.get_full_name() or t.patient.email, 'patient_email': t.patient.email, 'nutritionist_name': t.nutritionist.get_full_name() if t.nutritionist else 'Unknown', 'date': t.date.isoformat(), 'date_display': t.date.strftime('%b %d, %Y • %I:%M %p'), 'status': t.status, 'notes': t.notes, 'rejection_reason': getattr(t, 'rejection_reason', None), 'created_at': t.created_at.isoformat()} for t in trials])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_trial_request(request, trial_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    try:
        trial = Consultation.objects.get(id=trial_id, is_trial=True)
    except Consultation.DoesNotExist:
        return Response({'error': 'Trial request not found'}, status=404)
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    if action == 'approve':
        trial.status = 'confirmed'
        trial.admin_approved_at = timezone.now()
        title = '✅ Trial Consultation Approved'
        message = f'Your free trial consultation on {trial.date.strftime("%b %d, %Y at %I:%M %p")} has been approved.'
        Notification.objects.create(user=trial.patient, notification_type='consultation_update', title=title, message=message, related_id=trial.id)
        if trial.nutritionist:
            Notification.objects.create(nutritionist=trial.nutritionist, notification_type='consultation_reminder', title=title, message=f'Trial consultation with {trial.patient.get_full_name()} on {trial.date.strftime("%b %d, %Y at %I:%M %p")} has been approved by admin.', related_patient=trial.patient, related_id=trial.id, is_read=False)
    elif action == 'reject':
        trial.status = 'rejected'
        trial.rejection_reason = reason
        title = '❌ Trial Consultation Update'
        message = f'Your free trial consultation request was not approved. Reason: {reason}'
        Notification.objects.create(user=trial.patient, notification_type='consultation_update', title=title, message=message, related_id=trial.id)
        if trial.nutritionist:
            Notification.objects.create(nutritionist=trial.nutritionist, notification_type='consultation_reminder', title=title, message=f'Trial consultation request from {trial.patient.get_full_name()} on {trial.date.strftime("%b %d, %Y at %I:%M %p")} was rejected by admin. Reason: {reason}', related_patient=trial.patient, related_id=trial.id, is_read=False)
    else:
        return Response({'error': 'Invalid action'}, status=400)
    trial.save()
    return Response({'success': True, 'message': f'Trial {action}d successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_stats(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    total = Consultation.objects.filter(is_trial=True).count()
    approved = Consultation.objects.filter(is_trial=True, status='confirmed').count()
    rejected = Consultation.objects.filter(is_trial=True, status='rejected').count()
    pending = Consultation.objects.filter(is_trial=True, status='pending').count()
    return Response({'total': total, 'approved': approved, 'rejected': rejected, 'pending': pending})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_subscriptions(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Prendre UNIQUEMENT le dernier abonnement actif par patient
    subscriptions = PatientSubscription.objects.filter(status='active').order_by('-created_at')
    
    # Dédoublonner par patient
    unique_by_patient = {}
    for sub in subscriptions:
        patient_id = sub.patient.id
        if patient_id not in unique_by_patient:
            unique_by_patient[patient_id] = sub
    
    data = []
    for sub in unique_by_patient.values():
        patient = sub.patient
        profile = getattr(patient, 'user_profile', None)
        has_ai = profile.has_ai_tracker if profile else False
        has_consultations = profile.has_consultations if profile else False
        data.append({
            'id': sub.id,
            'customer_name': patient.get_full_name() or patient.email.split('@')[0],
            'customer_email': patient.email,
            'patient_name': patient.get_full_name(),
            'patient_email': patient.email,
            'plan_name': sub.plan_name,
            'plan': sub.plan_name,
            'total_amount': float(sub.price_paid),
            'price_paid': float(sub.price_paid),
            'duration_months': sub.duration_months,
            'duration': sub.duration_months,
            'start_date': sub.start_date,
            'end_date': sub.end_date,
            'created_at': sub.created_at,
            'status': sub.status,
            'has_ai': has_ai,
            'has_consultations': has_consultations,
            'include_ai': has_ai,
            'include_consultations': has_consultations
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignment_requests_admin(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    requests = AssignmentRequest.objects.filter(status='pending').select_related('patient', 'nutritionist').order_by('-created_at')
    return Response([{'id': req.id, 'patient_id': req.patient.id, 'patient_name': req.patient.get_full_name() or req.patient.email, 'patient_email': req.patient.email, 'nutritionist_id': req.nutritionist.id, 'nutritionist_name': req.nutritionist.get_full_name() or req.nutritionist.email, 'nutritionist_email': req.nutritionist.email, 'created_at': req.created_at.isoformat(), 'created_at_display': req.created_at.strftime('%b %d, %Y at %I:%M %p'), 'status': req.status} for req in requests])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_assignment_request_admin(request, request_id):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        assignment_req = AssignmentRequest.objects.get(id=request_id)
    except AssignmentRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=404)
    
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    alternative_nutritionist_id = request.data.get('alternative_nutritionist_id')
    
    if action == 'approve':
        # Approuver avec le nutritionniste demandé ou alternatif
        if alternative_nutritionist_id:
            try:
                nutritionist = User.objects.get(id=alternative_nutritionist_id, profile__role='nutritionist')
            except User.DoesNotExist:
                return Response({'error': 'Alternative nutritionist not found'}, status=404)
        else:
            nutritionist = assignment_req.nutritionist
        
        # Créer l'assignation
        assignment, created = PatientAssignment.objects.get_or_create(
            patient=assignment_req.patient, 
            nutritionist=nutritionist, 
            defaults={'is_active': True}
        )
        if not created and not assignment.is_active:
            assignment.is_active = True
            assignment.save()
        
        assignment_req.status = 'approved'
        assignment_req.save()
        
        # Notification au patient
        Notification.objects.create(
            user=assignment_req.patient, 
            notification_type='assignment_approved', 
            title='✅ Nutritionist Assigned!', 
            message=f'You have been assigned to {nutritionist.get_full_name() or nutritionist.email}.',
            related_id=nutritionist.id, 
            is_read=False
        )
        # Notification au nutritionniste
        Notification.objects.create(
            nutritionist=nutritionist, 
            notification_type='new_patient_assigned', 
            title='👤 New Patient Assigned!', 
            message=f'{assignment_req.patient.get_full_name()} has been assigned to you.',
            related_patient=assignment_req.patient, 
            related_id=assignment_req.patient.id, 
            is_read=False
        )
        
        return Response({'success': True, 'message': f'Patient assigned to {nutritionist.get_full_name()}'})
    
    elif action == 'reject':
        # Rejeter et éventuellement assigner un autre nutritionniste
        if alternative_nutritionist_id:
            try:
                nutritionist = User.objects.get(id=alternative_nutritionist_id, profile__role='nutritionist')
                # Créer l'assignation avec le nutritionniste alternatif
                assignment, created = PatientAssignment.objects.get_or_create(
                    patient=assignment_req.patient, 
                    nutritionist=nutritionist, 
                    defaults={'is_active': True}
                )
                if not created and not assignment.is_active:
                    assignment.is_active = True
                    assignment.save()
                
                # Notification au patient (assigné à un autre nutritionniste)
                Notification.objects.create(
                    user=assignment_req.patient, 
                    notification_type='assignment_approved', 
                    title='✅ Nutritionist Assigned!', 
                    message=f'Your request was reviewed. You have been assigned to {nutritionist.get_full_name() or nutritionist.email}. Reason: {reason}',
                    related_id=nutritionist.id, 
                    is_read=False
                )
                # Notification au nutritionniste alternatif
                Notification.objects.create(
                    nutritionist=nutritionist, 
                    notification_type='new_patient_assigned', 
                    title='👤 New Patient Assigned!', 
                    message=f'{assignment_req.patient.get_full_name()} has been assigned to you by admin.',
                    related_patient=assignment_req.patient, 
                    related_id=assignment_req.patient.id, 
                    is_read=False
                )
            except User.DoesNotExist:
                pass
        else:
            # Pas de nutritionniste alternatif - simple rejet
            Notification.objects.create(
                user=assignment_req.patient, 
                notification_type='assignment_rejected', 
                title='❌ Assignment Request Rejected', 
                message=f'Your request was rejected. Reason: {reason}',
                related_id=assignment_req.id, 
                is_read=False
            )
        
        assignment_req.status = 'rejected'
        assignment_req.rejection_reason = reason
        assignment_req.save()
        
        return Response({'success': True, 'message': 'Request processed successfully'})
    
    return Response({'error': 'Invalid action'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignment_stats(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    pending = AssignmentRequest.objects.filter(status='pending').count()
    approved = AssignmentRequest.objects.filter(status='approved').count()
    rejected = AssignmentRequest.objects.filter(status='rejected').count()
    total = AssignmentRequest.objects.count()
    return Response({'pending': pending, 'approved': approved, 'rejected': rejected, 'total': total})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_activities(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Récupérer les activités récentes (ex: dernières inscriptions, paiements, etc.)
    recent_users = User.objects.filter(profile__role='client').order_by('-date_joined')[:5]
    recent_payments = PatientSubscription.objects.filter().order_by('-created_at')[:5]
    
    activities = []
    
    for user in recent_users:
        activities.append({
            'description': f'👤 New user registered: {user.get_full_name() or user.email}',
            'time_ago': get_time_ago(user.date_joined)
        })
    
    for payment in recent_payments:
        activities.append({
            'description': f'💳 Subscription payment: ${payment.price_paid} - {payment.plan_name}',
            'time_ago': get_time_ago(payment.created_at)
        })
    
    # Si pas assez d'activités, ajouter des exemples
    if len(activities) < 5:
        activities.append({'description': '👩‍⚕️ New nutritionist pending verification', 'time_ago': '2 hours ago'})
        activities.append({'description': '📝 New blog post published', 'time_ago': 'Yesterday'})
    
    return Response({'activities': activities[:10]})

from nutritionists.models import Notification  # Ajoute cet import en haut si pas déjà

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_admin_notifications_read(request):
    """Marque toutes les notifications admin non lues comme lues"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Marquer toutes les notifications admin non lues comme lues
    updated = Notification.objects.filter(
        is_admin_notification=True,
        is_read=False
    ).update(is_read=True)
    
    return Response({
        'success': True, 
        'message': f'{updated} notifications marked as read',
        'updated_count': updated
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_notifications(request):
    """Récupère les notifications pour l'admin"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Récupérer les notifications admin non lues + quelques récentes
    notifications = Notification.objects.filter(
        is_admin_notification=True
    ).order_by('-created_at')[:30]
    
    unread_count = Notification.objects.filter(
        is_admin_notification=True, 
        is_read=False
    ).count()
    
    return Response({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'time_ago': get_time_ago(n.created_at),
            'is_read': n.is_read,
            'type': n.notification_type,
            'created_at': n.created_at.isoformat()
        } for n in notifications],
        'unread_count': unread_count
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_admin_notification_read(request, notification_id):
    """Marque une notification spécifique comme lue"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        notification = Notification.objects.get(id=notification_id, is_admin_notification=True)
        notification.is_read = True
        notification.save()
        return Response({'success': True, 'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)

def get_time_ago(dt):
    if not dt:
        return 'Just now'
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_standard_plans(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # TEMPORAIRE : retourne TOUS les plans diet_plan pour tester
    pending_plans = SpecialOffer.objects.filter(offer_type='diet_plan').order_by('-created_at')
    
    print(f"🔍 Nombre total de plans diet_plan: {pending_plans.count()}")
    
    result = []
    for plan in pending_plans:
        extra_data = plan.extra_data if plan.extra_data else {}
        result.append({
            'id': plan.id,
            'plan_name': plan.name,
            'description': plan.description,
            'submitted_by': plan.submitted_by.get_full_name() or plan.submitted_by.email if plan.submitted_by else 'System',
            'submitted_by_name': extra_data.get('submitted_by_name', ''),
            'submitted_at': plan.submitted_at.isoformat() if plan.submitted_at else plan.created_at.isoformat(),
            'submitted_at_display': (plan.submitted_at or plan.created_at).strftime('%b %d, %Y at %I:%M %p'),
            'duration_weeks': extra_data.get('duration_weeks', 4),
            'sport_advice': extra_data.get('sport_advice', ''),
            'weekly_program': extra_data.get('weekly_program', {})
        })
    
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_standard_plan(request, plan_id):
    """Approuver un plan standard"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        plan = SpecialOffer.objects.get(id=plan_id, offer_type='diet_plan')
    except SpecialOffer.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)
    
    plan.is_active = True
    plan.save()
    
    # Notification au nutritionniste
    if plan.submitted_by:
        Notification.objects.create(
            user=plan.submitted_by,
            notification_type='plan_updated',
            title='✅ Your Standard Plan Has Been Approved!',
            message=f'Your standard plan "{plan.name}" has been approved by admin and is now available to patients.',
            related_id=plan.id,
            is_read=False
        )
    
    # Notification admin (optionnel)
    Notification.objects.create(
        nutritionist=None,
        notification_type='admin_notification',
        title='✅ Plan Approved',
        message=f'Standard plan "{plan.name}" has been approved.',
        related_id=plan.id,
        is_read=False,
        is_admin_notification=True
    )
    
    return Response({'success': True, 'message': f'Plan "{plan.name}" approved'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_standard_plan(request, plan_id):
    """Rejeter un plan standard"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        plan = SpecialOffer.objects.get(id=plan_id, offer_type='diet_plan')
    except SpecialOffer.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)
    
    reason = request.data.get('reason', 'No reason provided')
    
    # Stocker la raison dans extra_data
    extra_data = plan.extra_data or {}
    extra_data['rejection_reason'] = reason
    extra_data['rejected_at'] = timezone.now().isoformat()
    plan.extra_data = extra_data
    plan.is_active = False
    plan.save()
    
    # Notification au nutritionniste
    if plan.submitted_by:
        Notification.objects.create(
            user=plan.submitted_by,
            notification_type='plan_updated',
            title='❌ Your Standard Plan Has Been Rejected',
            message=f'Your standard plan "{plan.name}" was rejected by admin. Reason: {reason}',
            related_id=plan.id,
            is_read=False
        )
    
    return Response({'success': True, 'message': f'Plan "{plan.name}" rejected'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_diet_plans(request):
    """Récupère tous les plans diététiques (approuvés et rejetés)"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Récupérer TOUS les plans (is_active=True sont approuvés, is_active=False sont rejetés/en attente)
    # Mais on ne veut que ceux qui ont été traités (approuvés ou rejetés)
    # Un plan est "traité" s'il a été approuvé (is_active=True) ou rejeté (avec une raison)
    from django.db.models import Q
    all_plans = SpecialOffer.objects.filter(
        offer_type='diet_plan'
    ).filter(
        Q(is_active=True) | Q(extra_data__has_key='rejection_reason')
    ).order_by('-created_at')
    
    result = []
    for plan in all_plans:
        extra_data = plan.extra_data if plan.extra_data else {}
        
        # Déterminer le statut
        if plan.is_active:
            status = "approved"
            rejection_reason = None
        else:
            status = "rejected"
            rejection_reason = extra_data.get('rejection_reason', 'No reason provided')
        
        result.append({
            'id': plan.id,
            'plan_name': plan.name,
            'type': 'standard',
            'submitted_by': plan.submitted_by.get_full_name() or plan.submitted_by.email if plan.submitted_by else 'Admin',
            'duration_weeks': extra_data.get('duration_weeks', 4),
            'status': status,
            'rejection_reason': rejection_reason,
            'created_at': plan.created_at.isoformat()
        })
    
    return Response(result)