"""
AI Calorie Estimation Module - CORRECTED VERSION
"""

import csv
import os
import numpy as np
from ultralytics import YOLO

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, 'best.pt')
CSV_PATH = os.path.join(CURRENT_DIR, 'food_data.csv')

print("🚀 Loading AI model...")
model = YOLO(MODEL_PATH)
print("✅ Model loaded successfully!")

# Load nutritional database
food_db = {}
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['food_name'].lower().strip()
        food_db[name] = {
            'calories_per_100g': float(row['calories_per_100g']),
            'thickness_factor': float(row['thickness_factor']),
            'typical_portion_g': float(row['typical_portion_g'])
        }

print(f"✅ Loaded {len(food_db)} food categories")

# FIXED: Increased default pixels (for close-up phone photos)
DEFAULT_TYPICAL_PIXELS = 10000  # Changed from 5000 to 10000

# Maximum realistic calories per food
MAX_CALORIES_PER_FOOD = {
    'rice': 350,
    'pizza': 500,
    'bread': 200,
    'pasta': 400,
    'potato': 300,
    'chicken duck': 350,
    'steak': 400,
    'fish': 350,
    'cake': 400,
    'ice cream': 300,
    'pork': 400,
    'sausage': 350,
    'fried meat': 400,
    'noodles': 400,
    'french fries': 400,
}

# ============================================
# Main function
# ============================================

def analyze_meal(image_path):
    try:
        results = model(image_path)
        
        detected_foods = []
        total_calories = 0
        
        for r in results:
            if r.masks is None:
                continue
            
            boxes = r.boxes
            masks = r.masks.data.cpu().numpy()
            
            for i, mask in enumerate(masks):
                class_id = int(boxes.cls[i])
                class_name = r.names[class_id].lower().strip()
                mask_pixels = np.sum(mask > 0)
                
                food_info = food_db.get(class_name)
                if not food_info:
                    continue
                
                # ===== Estimate Weight =====
                ratio = mask_pixels / DEFAULT_TYPICAL_PIXELS
                estimated_weight = food_info['typical_portion_g'] * ratio
                estimated_weight = estimated_weight * food_info['thickness_factor']
                
                # FIXED: Lower max weight (300g instead of 500g)
                estimated_weight = max(estimated_weight, 10)
                estimated_weight = min(estimated_weight, 300)  # Changed from 500 to 300
                
                # ===== Estimate Calories =====
                calories_per_100g = food_info['calories_per_100g']
                calories = (estimated_weight / 100) * calories_per_100g
                calories = round(calories, 0)
                
                # FIXED: Apply maximum calorie limit per food
                if class_name in MAX_CALORIES_PER_FOOD:
                    calories = min(calories, MAX_CALORIES_PER_FOOD[class_name])
                
                # ===== Confidence Score =====
                prob = float(boxes.conf[i]) if hasattr(boxes, 'conf') else 0.8
                confidence = prob
                if mask_pixels < 2000:  # Increased threshold
                    confidence *= 0.7
                elif mask_pixels < 4000:
                    confidence *= 0.9
                confidence = round(min(confidence, 1.0), 2)
                
                detected_foods.append({
                    'name': class_name,
                    'weight_g': round(estimated_weight, 1),
                    'calories': int(calories),
                    'confidence': confidence,
                })
                
                total_calories += calories
        
        # Calorie range ±15%
        range_min = int(total_calories * 0.85)
        range_max = int(total_calories * 1.15)
        
        return {
            'success': True,
            'foods': detected_foods,
            'total_calories': int(total_calories),
            'calorie_range': f"{range_min}-{range_max} kcal",
            'food_count': len(detected_foods),
            'message': f"Detected {len(detected_foods)} food items"
        }
        
    except Exception as e:
        return {
            'success': False,
            'foods': [],
            'total_calories': 0,
            'calorie_range': "0-0 kcal",
            'food_count': 0,
            'message': f"Error: {str(e)}"
        }

def print_result(result):
    print("\n" + "="*50)
    print("Analysis Result:")
    print("="*50)
    if result['success']:
        for food in result['foods']:
            print(f"🍽️ {food['name']}: {food['weight_g']}g → {food['calories']} kcal")
        print("-"*30)
        print(f"📊 Total: {result['total_calories']} kcal")
        print(f"📊 Range: {result['calorie_range']}")
    else:
        print(f"❌ {result['message']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = analyze_meal(sys.argv[1])
        print_result(result)
    else:
        print("Usage: python calorie_ai.py <image_path>")