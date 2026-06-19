# consultations/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Consultation, NutritionistProfile
from django.contrib.auth import get_user_model
from nutritionists.models import Notification, AssignmentRequest, PatientAssignment
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionists(request):
    nutritionists = User.objects.filter(profile__role='nutritionist')
    data = []
    for n in nutritionists:
        profile = getattr(n, 'nutritionist_profile', None)
        data.append({'id': n.id, 'name': n.get_full_name(), 'email': n.email, 'specialization': profile.specialization if profile else 'General Nutrition', 'bio': profile.bio if profile else '', 'experience_years': profile.experience_years if profile else 0, 'is_available': profile.is_available if profile else True})
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutritionist_profile(request):
    if request.user.role != 'nutritionist':
        return Response({'error': 'Unauthorized'}, status=403)
    profile = getattr(request.user, 'nutritionist_profile', None)
    return Response({'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email, 'phone': request.user.phone, 'country': request.user.country, 'specialization': profile.specialization if profile else '', 'experience_years': profile.experience_years if profile else 0, 'bio': profile.bio if profile else '', 'is_available': profile.is_available if profile else True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_consultations(request):
    consultations = Consultation.objects.filter(patient=request.user).order_by('-created_at')
    
    result = []
    for c in consultations:
        # Formater la date pour l'affichage
        date_display = None
        if c.date:
            date_display = c.date.strftime('%Y-%m-%d %H:%M')
        
        result.append({
            'id': c.id,
            'nutritionist_name': c.nutritionist.get_full_name() or c.nutritionist.email.split('@')[0] if c.nutritionist else 'Unknown',
            'date': date_display,
            'status': c.status,
            'zoom_link': c.zoom_link,
            'notes': c.notes,
            'rejection_reason': getattr(c, 'rejection_reason', None),
            'alternative_date': getattr(c, 'alternative_date', None),
            'alternative_time': getattr(c, 'alternative_time', None)
        })
    
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_consultation(request):
    nutritionist_id = request.data.get('nutritionist_id')
    date_str = request.data.get('date')
    notes = request.data.get('notes', '')
    
    if not nutritionist_id or not date_str:
        return Response({'error': 'Nutritionist and date are required'}, status=400)
    
   
    try:
        if request.user.profile.role != 'client':
            return Response({'error': 'Only patients can book consultations'}, status=403)
    except AttributeError:
        return Response({'error': 'Profile not found'}, status=403)
    
    # Récupérer le nutritionniste
    try:
        nutritionist = User.objects.get(id=nutritionist_id, profile__role='nutritionist')
    except User.DoesNotExist:
        return Response({'error': 'Nutritionist not found'}, status=404)
    
    # Convertir la date
    try:
        consultation_date = datetime.fromisoformat(date_str)
        if timezone.is_naive(consultation_date):
            consultation_date = timezone.make_aware(consultation_date)
    except Exception as e:
        return Response({'error': f'Invalid date format: {str(e)}'}, status=400)
    
    # Vérifier que la date est dans le futur
    if consultation_date < timezone.now():
        return Response({'error': 'Date must be in the future'}, status=400)
    
    # Créer la consultation
    consultation = Consultation.objects.create(
        patient=request.user,
        nutritionist=nutritionist,
        date=consultation_date,
        status='pending',
        notes=notes,
        is_trial=False,  # ← Important : pas une consultation trial
        zoom_link=None
    )
    
    # 🔔 NOTIFICATION POUR LE NUTRITIONNISTE
    from nutritionists.models import Notification
    Notification.objects.create(
        nutritionist=nutritionist,
        notification_type='consultation_reminder',
        title='🔔 New Consultation Request',
        message=f'{request.user.get_full_name() or request.user.email} has requested a consultation on {consultation_date.strftime("%B %d, %Y at %I:%M %p")}.',
        related_patient=request.user,
        related_id=consultation.id,
        is_read=False
    )
    
    return Response({
        'message': 'Consultation requested successfully!', 
        'consultation_id': consultation.id, 
        'status': consultation.status
    }, status=201)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def cancel_consultation(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=request.user)
    if consultation.status == 'cancelled':
        return Response({'error': 'Consultation already cancelled'}, status=400)
    consultation.status = 'cancelled'
    consultation.save()
    return Response({'message': 'Consultation cancelled successfully'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_trial_consultation(request):
    data = request.data
    user = request.user
    
    # Vérifier si l'utilisateur a déjà un trial
    existing_trial = Consultation.objects.filter(
        patient=user, 
        is_trial=True, 
        status__in=['pending', 'confirmed']
    ).exists()
    
    if existing_trial:
        return Response({
            'success': False, 
            'error': 'You have already booked a free trial consultation. Only one trial per user.',
            'already_booked': True
        }, status=400)
    
    date_str = data.get('slot_date')
    time_str = data.get('slot_time')
    nutritionist_id = data.get('nutritionist_id')
    notes = data.get('notes', '')
    
    if not date_str or not time_str:
        return Response({'success': False, 'error': 'Date and time are required'}, status=400)
    
    try:
        consultation_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except:
        return Response({'error': 'Invalid date format'}, status=400)
    
    # Créer la consultation trial
    consultation = Consultation.objects.create(
        patient=user,
        nutritionist_id=nutritionist_id if nutritionist_id else None,
        date=consultation_date,
        is_trial=True,
        status='pending',
        notes=f"Free trial consultation requested by {user.email}\nAdditional notes: {notes}"
    )
    
    # 🔔 NOTIFICATION POUR LE NUTRITIONNISTE (dans son dashboard)
    if nutritionist_id:
        from nutritionists.models import Notification
        Notification.objects.create(
            nutritionist_id=nutritionist_id,
            notification_type='consultation_reminder',
            title='🔔 New Free Trial Request!',
            message=f'{user.get_full_name() or user.email} has requested a FREE TRIAL consultation on {date_str} at {time_str}. Please confirm or reject.',
            related_patient=user,
            related_id=consultation.id,
            is_read=False
        )
    
    return Response({
        'success': True, 
        'message': 'Free trial requested! The nutritionist will confirm soon.',
        'consultation_id': consultation.id
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_status(request):
    trial = Consultation.objects.filter(
        patient=request.user, 
        is_trial=True
    ).order_by('-created_at').first()
    
    if trial:
        return Response({
            'has_booked_trial': True,
            'trial_info': {
                'id': trial.id,
                'nutritionist_name': trial.nutritionist.get_full_name() if trial.nutritionist else 'Pending assignment',
                'date': trial.date.strftime('%B %d, %Y') if trial.date else None,
                'time': trial.date.strftime('%I:%M %p') if trial.date else None,
                'status': trial.status,
                'created_at': trial.created_at.isoformat()
            }
        })
    return Response({'has_booked_trial': False, 'trial_info': None})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_nutritionist_assignment(request):
    user = request.user
    if user.role != 'patient':
        return Response({'error': 'Only patients can request a nutritionist'}, status=403)
    nutritionist_id = request.data.get('nutritionist_id')
    if not nutritionist_id:
        return Response({'error': 'Nutritionist ID required'}, status=400)
    try:
        nutritionist = User.objects.get(id=nutritionist_id, role='nutritionist')
    except User.DoesNotExist:
        return Response({'error': 'Nutritionist not found'}, status=404)
    AssignmentRequest.objects.filter(patient=user, status='pending').delete()
    assignment_request = AssignmentRequest.objects.create(patient=user, nutritionist=nutritionist, status='pending')
    Notification.objects.create(nutritionist=None, notification_type='assignment_request', title='🔔 New Assignment Request', message=f'{user.get_full_name() or user.email} wants to be assigned to {nutritionist.get_full_name() or nutritionist.email}.', related_patient=user, related_id=assignment_request.id, is_read=False)
    return Response({'success': True, 'message': 'Your request has been sent to admin. You will be notified once approved.', 'request_id': assignment_request.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_requests(request):
    """Récupère les demandes de consultation en attente pour le nutritionniste"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    pending_consultations = Consultation.objects.filter(
        nutritionist=request.user,
        status='pending',
        is_trial=False
    ).select_related('patient').order_by('date')
    
    return Response([{
        'id': c.id,
        'patient_id': c.patient.id,
        'patient_name': c.patient.get_full_name() or c.patient.email.split('@')[0],
        'date': c.date.strftime('%Y-%m-%d') if c.date else None,
        'time': c.date.strftime('%H:%M') if c.date else None,
        'status': c.status,
        'notes': c.notes,
        
    } for c in pending_consultations])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_requests(request):
    """Récupère les demandes de consultation trial en attente pour le nutritionniste"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    trial_consultations = Consultation.objects.filter(
        nutritionist=request.user,
        status='pending',
        is_trial=True
    ).select_related('patient').order_by('date')
    
    return Response([{
        'id': c.id,
        'patient_id': c.patient.id,
        'patient_name': c.patient.get_full_name() or c.patient.email.split('@')[0],
        'date': c.date.strftime('%Y-%m-%d') if c.date else None,
        'time': c.date.strftime('%H:%M') if c.date else None,
        'status': c.status,
        'notes': c.notes
    } for c in trial_consultations])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_upcoming_consultations(request):
    """Récupère les consultations confirmées à venir pour le nutritionniste"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    now = timezone.now()
    upcoming = Consultation.objects.filter(
        nutritionist=request.user,
        status='confirmed',
        date__gte=now
    ).select_related('patient').order_by('date')
    
    return Response([{
        'id': c.id,
        'patient_id': c.patient.id,
        'patient_name': c.patient.get_full_name() or c.patient.email.split('@')[0],
        'date': c.date.strftime('%Y-%m-%d') if c.date else None,
        'time': c.date.strftime('%H:%M') if c.date else None,
        'zoom_link': c.zoom_link,
        'status': c.status
    } for c in upcoming])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_completed_consultations(request):
    """Récupère les consultations complétées pour le nutritionniste"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    completed = Consultation.objects.filter(
        nutritionist=request.user,
        status='completed'
    ).select_related('patient').order_by('-date')[:50]
    
    return Response([{
        'id': c.id,
        'patient_id': c.patient.id,
        'patient_name': c.patient.get_full_name() or c.patient.email.split('@')[0],
        'date': c.date.strftime('%Y-%m-%d') if c.date else None,
        'time': c.date.strftime('%H:%M') if c.date else None,
        'notes': c.nutritionist_notes,
        'status': c.status
    } for c in completed])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weekly_consultation_counts(request):
    """Récupère le nombre de consultations par jour pour la semaine"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    end_of_week = start_of_week + timezone.timedelta(days=6)
    
    consultations = Consultation.objects.filter(
        nutritionist=request.user,
        date__date__range=[start_of_week, end_of_week]
    )
    
    # Compter par date
    from collections import Counter
    date_counts = Counter([c.date.date().isoformat() for c in consultations if c.date])
    
    return Response([{
        'date': date,
        'count': count
    } for date, count in date_counts.items()])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_consultations_by_date(request):
    """Récupère les consultations pour une date spécifique"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    date_str = request.GET.get('date')
    if not date_str:
        return Response({'error': 'Date required'}, status=400)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return Response({'error': 'Invalid date format'}, status=400)
    
    consultations = Consultation.objects.filter(
        nutritionist=request.user,
        date__date=target_date
    ).select_related('patient').order_by('date')
    
    return Response([{
        'id': c.id,
        'patient_id': c.patient.id,
        'patient_name': c.patient.get_full_name() or c.patient.email.split('@')[0],
        'date': c.date.strftime('%Y-%m-%d') if c.date else None,
        'time': c.date.strftime('%H:%M') if c.date else None,
        'zoom_link': c.zoom_link,
        'status': c.status
    } for c in consultations])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_consultation(request, consult_id):
    """Répondre à une demande de consultation (accepter ou rejeter)"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    try:
        consultation = Consultation.objects.get(id=consult_id, nutritionist=request.user, status='pending')
    except Consultation.DoesNotExist:
        return Response({'error': 'Consultation not found'}, status=404)
    
    action = request.data.get('action')
    new_date = request.data.get('new_date')
    new_time = request.data.get('new_time')
    zoom_link = request.data.get('zoom_link')
    reason = request.data.get('reason')
    alternative_date = request.data.get('alternative_date')
    alternative_time = request.data.get('alternative_time')
    
    from nutritionists.models import Notification
    
    if action == 'accept':
        consultation.status = 'confirmed'
        
        # Mettre à jour la date si fournie
        new_datetime_str = None
        if new_date and new_time:
            try:
                new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
                consultation.date = timezone.make_aware(new_datetime)
                new_datetime_str = consultation.date.strftime("%B %d, %Y at %I:%M %p")
            except:
                pass
        else:
            new_datetime_str = consultation.date.strftime("%B %d, %Y at %I:%M %p") if consultation.date else None
        
        if zoom_link:
            consultation.zoom_link = zoom_link
        
        consultation.save()
        
        # 🔔 NOTIFICATION POUR LE PATIENT - ACCEPTATION
        Notification.objects.create(
            user=consultation.patient,
            notification_type='consultation_update',
            title='✅ Consultation Confirmed!',
            message=f'Your consultation with {request.user.get_full_name()} on {new_datetime_str or "the scheduled date"} has been CONFIRMED.\n\n' + (f'🔗 Zoom link: {zoom_link}' if zoom_link else 'You will receive the Zoom link before the session.'),
            related_id=consultation.id,
            is_read=False
        )
        
        return Response({'success': True, 'message': 'Consultation confirmed and patient notified'})
    
    elif action == 'reject':
        consultation.status = 'rejected'
        consultation.rejection_reason = reason
        consultation.save()
        
        # Construire le message pour le patient
        message = f'❌ Your consultation request was rejected by {request.user.get_full_name()}.'
        if reason:
            message += f'\n\n📌 Reason: {reason}'
        if alternative_date and alternative_time:
            message += f'\n\n💡 Alternative proposed: {alternative_date} at {alternative_time}. Please book a new slot if this works for you.'
        
        # 🔔 NOTIFICATION POUR LE PATIENT - REJET
        Notification.objects.create(
            user=consultation.patient,
            notification_type='consultation_update',
            title='❌ Consultation Request Rejected',
            message=message,
            related_id=consultation.id,
            is_read=False
        )
        
        return Response({'success': True, 'message': 'Consultation rejected and patient notified'})
    
    return Response({'error': 'Invalid action'}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_consultation(request, consult_id):
    """Annuler ou reprogrammer une consultation existante"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    try:
        consultation = Consultation.objects.get(id=consult_id, nutritionist=request.user, status='confirmed')
    except Consultation.DoesNotExist:
        return Response({'error': 'Consultation not found'}, status=404)
    
    reason = request.data.get('reason')
    new_date = request.data.get('new_date')
    new_time = request.data.get('new_time')
    new_zoom_link = request.data.get('zoom_link')
    
    from nutritionists.models import Notification
    
    old_date_str = consultation.date.strftime('%B %d, %Y at %I:%M %p') if consultation.date else 'TBD'
    
    # Mettre à jour la consultation
    new_datetime_str = old_date_str
    if new_date and new_time:
        try:
            new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            consultation.date = timezone.make_aware(new_datetime)
            new_datetime_str = consultation.date.strftime('%B %d, %Y at %I:%M %p')
        except:
            pass
    
    if new_zoom_link:
        consultation.zoom_link = new_zoom_link
    
    consultation.save()
    
    # 🔔 NOTIFICATION POUR LE PATIENT - MODIFICATION
    message = f'🔄 Your consultation has been UPDATED.\n\n'
    message += f'📅 Original: {old_date_str}\n'
    message += f'📅 New date: {new_datetime_str}\n'
    if reason:
        message += f'\n📌 Reason: {reason}\n'
    if new_zoom_link:
        message += f'\n🔗 New Zoom link: {new_zoom_link}'
    
    Notification.objects.create(
        user=consultation.patient,
        notification_type='consultation_update',
        title='🔄 Consultation Updated',
        message=message,
        related_id=consultation.id,
        is_read=False
    )
    
    return Response({'success': True, 'message': 'Consultation updated and patient notified'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_consultation(request, consult_id):
    """Marquer une consultation comme complétée"""
    try:
        if request.user.profile.role != 'nutritionist':
            return Response({'error': 'Unauthorized'}, status=403)
    except:
        return Response({'error': 'Profile not found'}, status=403)
    
    try:
        consultation = Consultation.objects.get(id=consult_id, nutritionist=request.user, status='confirmed')
    except Consultation.DoesNotExist:
        return Response({'error': 'Consultation not found'}, status=404)
    
    notes = request.data.get('notes', '')
    
    consultation.status = 'completed'
    consultation.nutritionist_notes = notes
    consultation.save()
    
    # Créer un rapport hebdomadaire
    try:
        from consultations.models import WeeklyReport
        WeeklyReport.objects.create(
            nutritionist=request.user,
            patient=consultation.patient,
            content=notes
        )
    except:
        pass
    
    # 🔔 NOTIFICATION POUR LE PATIENT - COMPLÉTION
    from nutritionists.models import Notification
    Notification.objects.create(
        user=consultation.patient,
        notification_type='consultation_update',
        title='✅ Consultation Completed',
        message=f'Your consultation with {request.user.get_full_name()} has been marked as COMPLETED.\n\n📝 Notes from the session:\n{notes if notes else "No notes provided."}\n\nThank you for using NutriLife!',
        related_id=consultation.id,
        is_read=False
    )
    
    return Response({'success': True, 'message': 'Consultation completed and patient notified'})