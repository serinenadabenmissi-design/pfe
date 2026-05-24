# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import UserProfile

def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about_us.html')

def feedback_view(request):
    return render(request, 'feedback.html')

def contact_view(request):
    return render(request, 'contact.html')

def blog(request):
    return render(request, 'blog.html')

def login_view(request):
    return render(request, 'login.html')

def register_view(request):
    return render(request, 'register.html')

def simple_cons(request):
    return render(request, 'simple_cons.html')

@login_required
def admin_dashboard_view(request):
    try:
        profile = request.user.profile
        role = profile.role
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, role='client')
        role = 'client'
    
    if role != 'admin' and not request.user.is_superuser:
        # Frame d'erreur simple - sans template 403
        return render(request, 'error_frame.html', {
            'error_code': 403,
            'error_title': 'Accès Refusé',
            'error_message': 'Cette page est réservée aux administrateurs. Vous n\'avez pas les autorisations nécessaires.',
            'redirect_url': '/login/'
        })
    
    return render(request, 'admindash.html', {'profile': profile})

@login_required
def nutritionist_dashboard_view(request):
    try:
        profile = request.user.profile
        role = profile.role
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, role='client')
        role = 'client'
    
    if role != 'nutritionist':
        # Frame d'erreur simple - sans template 403
        return render(request, 'error_frame.html', {
            'error_code': 403,
            'error_title': 'Accès Refusé',
            'error_message': 'Cette page est réservée aux nutritionnistes. Veuillez vous connecter avec un compte nutritionniste.',
            'redirect_url': '/login/'
        })
    
    return render(request, 'nutridash.html', {'profile': profile})

@login_required
def user_dashboard_view(request):
    try:
        profile = request.user.profile
        role = profile.role
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, role='client')
        role = 'client'
    
    if role not in ['client', 'patient']:
        # Frame d'erreur simple - sans template 403
        return render(request, 'error_frame.html', {
            'error_code': 403,
            'error_title': 'Accès Refusé',
            'error_message': 'Cette page est réservée aux patients. Vous n\'avez pas les autorisations nécessaires.',
            'redirect_url': '/login/'
        })
    
    return render(request, 'userdash.html', {'profile': profile})

@login_required
def select_nutritionist_view(request):
    return render(request, 'select_nutri.html')

@login_required
def trial_consultation_view(request):
    return render(request, 'trial-consultation.html')

@login_required
def payment_view(request):
    return render(request, 'payment.html')