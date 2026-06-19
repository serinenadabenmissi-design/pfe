# ai_tracker/views.py
import os
import uuid
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import date

# Import du module AI
import sys

MODEL_PATH = os.path.join(settings.BASE_DIR, 'ai_tracker', 'Model')
sys.path.insert(0, MODEL_PATH)

try:
    from calorie_ai import analyze_meal  # ← C'est calorie_ai.py, pas Model.py
    AI_AVAILABLE = True
    print("✅ AI Calorie Tracker loaded successfully")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI model not available: {e}")

# ✅ Importer FoodLog depuis users
from users.models import FoodLog


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_food_image(request):
    """Analyser une image de nourriture avec l'IA"""
    try:
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=400)
        
        image = request.FILES['image']
        
        if not image.content_type.startswith('image/'):
            return Response({'error': 'File must be an image'}, status=400)
        
        # Sauvegarder l'image temporairement
        image_id = uuid.uuid4().hex
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        image_path = os.path.join(temp_dir, f'{image_id}.jpg')
        
        with open(image_path, 'wb') as f:
            for chunk in image.chunks():
                f.write(chunk)
        
        # Analyser avec l'IA
        if AI_AVAILABLE:
            result = analyze_meal(image_path)
        else:
            # Mode simulation
            import random
            foods = [
                {'name': 'Grilled Chicken Salad', 'weight_g': 250, 'calories': 420, 'confidence': 0.94},
                {'name': 'Quinoa Bowl', 'weight_g': 320, 'calories': 520, 'confidence': 0.87},
                {'name': 'Salmon with Vegetables', 'weight_g': 280, 'calories': 485, 'confidence': 0.91},
                {'name': 'Oatmeal with Berries', 'weight_g': 220, 'calories': 320, 'confidence': 0.88},
                {'name': 'Avocado Toast with Egg', 'weight_g': 180, 'calories': 445, 'confidence': 0.85},
            ]
            selected = random.choice(foods)
            result = {
                'success': True,
                'foods': [selected],
                'total_calories': selected['calories'],
                'calorie_range': f"{int(selected['calories']*0.85)}-{int(selected['calories']*1.15)} kcal",
                'food_count': 1,
                'message': f"Detected 1 food item"
            }
        
        # Nettoyer le fichier temporaire
        os.remove(image_path)
        
        if result['success']:
            return Response({
                'success': True,
                'foods': result['foods'],
                'total_calories': result['total_calories'],
                'calorie_range': result['calorie_range'],
                'food_count': result['food_count']
            })
        else:
            return Response({'error': result['message']}, status=500)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_ai_meal(request):
    """Enregistrer le repas analysé par l'IA"""
    try:
        user = request.user
        data = request.data
        
        meal_type = data.get('meal_type', 'lunch')
        food_name = data.get('food_name', '')
        calories = data.get('calories', 0)
        
        if not food_name or not calories:
            return Response({'error': 'Food name and calories required'}, status=400)
        
        # ✅ Utiliser FoodLog depuis users.models
        food_log = FoodLog.objects.create(
            user=user,
            meal_type=meal_type,
            food_name=food_name,
            calories=int(calories),
            logged_at=timezone.now(),
            date=date.today()
        )
        
        return Response({
            'success': True,
            'message': 'Meal logged successfully',
            'log_id': food_log.id
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)