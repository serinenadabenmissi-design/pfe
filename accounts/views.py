# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser
from users.models import UserProfile

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        data = request.data
        email = data.get('email')
        
        if CustomUser.objects.filter(email=email).exists():
            return Response({'error': 'Email already registered'}, status=400)
        
        user = CustomUser.objects.create_user(
            email=email,
            password=data.get('password'),
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', '')
        )
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = data.get('role', 'client')
        profile.gender = data.get('gender', '')
        profile.weight = float(data.get('weight', 70))
        profile.height = float(data.get('height', 170))
        profile.phone = data.get('phone', '')
        # Dans register_user, ajoute cette ligne :
        profile.goal = float(data.get('goal', 70))  
        if data.get('healthConditions'):
            profile.health_conditions = data.get('healthConditions')
        
        profile.save()
        login(request, user)
        return Response({
            'message': 'Account created successfully',
            'user_id': user.id,
            'email': user.email,
            'role': profile.role
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)
    
    if user:
        login(request, user)
        try:
            # Le rôle est dans user.profile.role
            role = user.profile.role
        except:
            # Si pas de profil, créer un profil par défaut
            from users.models import UserProfile
            profile = UserProfile.objects.create(user=user, role='client')
            role = 'client'
        
        return Response({
            'message': 'Login success',
            'role': role,  # 'client', 'nutritionist', ou 'admin'
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }, status=200)
    return Response({'error': 'Invalid credentials'}, status=401)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    logout(request)
    return Response({'message': 'Logout success'}, status=200)