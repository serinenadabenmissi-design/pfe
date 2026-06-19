from calorie_ai import analyze_meal, quick_test

# ==== Test with your image ====
image_path = "test_image.jpg"  # Change this path

result = analyze_meal(image_path)

if result['success']:
    print("\n✅ Result:")
    print(f"   Foods: {result['foods']}")
    print(f"   Total: {result['total_calories']} kcal")
    print(f"   Range: {result['calorie_range']}")
else:
    print(f"❌ Error: {result['message']}")