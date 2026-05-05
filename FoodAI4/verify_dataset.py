import os
from pathlib import Path

YOLO_DATASET_DIR = r"C:\Users\Grand-PC\Desktop\FoodAI4\yolo_dataset"

print("=" * 60)
print("CLEAN DATASET VERIFICATION")
print("=" * 60)

total_images = 0
total_labels = 0

for split in ['train', 'val', 'test']:
    images_dir = os.path.join(YOLO_DATASET_DIR, "images", split)
    labels_dir = os.path.join(YOLO_DATASET_DIR, "labels", split)
    
    # Get unique images (avoid double counting jpg/jpeg)
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(Path(images_dir).glob(ext))
    
    # Remove duplicates by stem (filename without extension)
    unique_images = {f.stem: f for f in image_files}
    num_images = len(unique_images)
    num_labels = len(list(Path(labels_dir).glob('*.txt')))
    
    total_images += num_images
    total_labels += num_labels
    
    status = "✅ MATCH" if num_images == num_labels else "❌ MISMATCH"
    print(f"\n{split.upper()}: {num_images} images, {num_labels} labels - {status}")

print(f"\n{'='*60}")
print(f"TOTAL: {total_images} images, {total_labels} labels")
print(f"STATUS: {'✅ READY FOR TRAINING' if total_images == total_labels else '⚠️ ISSUES DETECTED'}")
print("=" * 60)