from calorie_ai import analyze_meal, print_result
import os

# Ask user for image path
image_path = input("📷 Enter image path: ").strip().strip('"').strip("'")

if os.path.exists(image_path):
    result = analyze_meal(image_path)
    print_result(result)
else:
    print(f"❌ Image not found: {image_path}")
    