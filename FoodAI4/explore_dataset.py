import json
import os
from collections import Counter

# Your FOODAI4 path
FOODAI4_PATH = r"C:\Users\Grand-PC\Desktop\FoodAI4"

# Input paths
TRAIN_JSON = os.path.join(FOODAI4_PATH, "annotations", "train.json")
TEST_JSON = os.path.join(FOODAI4_PATH, "annotations", "test.json")

# Output paths (save in same folder)
OUTPUT_DIR = os.path.join(FOODAI4_PATH, "filtered_dataset")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "annotations"), exist_ok=True)

TRAIN_JSON_OUT = os.path.join(OUTPUT_DIR, "annotations", "train_top50.json")
TEST_JSON_OUT = os.path.join(OUTPUT_DIR, "annotations", "test_top50.json")

print("=" * 70)
print("STEP 1: FILTERING TO TOP 50 CLASSES")
print("=" * 70)

# Load the JSON files
print("\n1. Loading original COCO annotation files...")
with open(TRAIN_JSON, 'r') as f:
    train_coco = json.load(f)

with open(TEST_JSON, 'r') as f:
    test_coco = json.load(f)

print(f"   ✓ Loaded training data: {len(train_coco['images'])} images, {len(train_coco['annotations'])} annotations")
print(f"   ✓ Loaded test data: {len(test_coco['images'])} images, {len(test_coco['annotations'])} annotations")

# Count instances per class in training set
print("\n2. Counting instances per class (training set only)...")
class_counts = Counter()
for ann in train_coco['annotations']:
    class_counts[ann['category_id']] += 1

# Get class names
class_names = {cat['id']: cat['name'] for cat in train_coco['categories']}

# Select top 50 classes
print("\n3. Selecting top 50 most frequent classes...")
top50_class_ids = [class_id for class_id, count in class_counts.most_common(50)]

# Create mapping from old ID to new ID (0-49)
old_to_new_id = {}
new_categories = []

print("\n   Top 50 classes selected:")
print("-" * 70)
print(f"{'New ID':<8} {'Old ID':<8} {'Count':<10} Class Name")
print("-" * 70)

for new_id, old_id in enumerate(top50_class_ids):
    old_to_new_id[old_id] = new_id
    count = class_counts[old_id]
    name = class_names[old_id]
    new_categories.append({"id": new_id, "name": name})
    print(f"{new_id:<8} {old_id:<8} {count:<10} {name}")

# Show statistics
removed_classes = set(class_names.keys()) - set(top50_class_ids)
removed_instances = sum(class_counts[class_id] for class_id in removed_classes)
total_instances = sum(class_counts.values())

print("\n" + "-" * 70)
print(f"\n📊 Statistics:")
print(f"   Original classes: {len(class_names)}")
print(f"   Kept classes: 50")
print(f"   Removed classes: {len(removed_classes)}")
print(f"\n   Original instances: {total_instances}")
print(f"   Instances in top 50: {total_instances - removed_instances} ({((total_instances - removed_instances)/total_instances)*100:.1f}%)")
print(f"   Removed instances: {removed_instances} ({(removed_instances/total_instances)*100:.1f}%)")

# Filter training annotations
print("\n4. Filtering training annotations...")
filtered_train_annotations = []
for ann in train_coco['annotations']:
    if ann['category_id'] in old_to_new_id:
        new_ann = ann.copy()
        new_ann['category_id'] = old_to_new_id[ann['category_id']]
        filtered_train_annotations.append(new_ann)

# Find which images still have annotations
valid_image_ids = set(ann['image_id'] for ann in filtered_train_annotations)

# Filter training images
filtered_train_images = [img for img in train_coco['images'] if img['id'] in valid_image_ids]

print(f"   Original training images: {len(train_coco['images'])}")
print(f"   Filtered training images: {len(filtered_train_images)}")
print(f"   Original annotations: {len(train_coco['annotations'])}")
print(f"   Filtered annotations: {len(filtered_train_annotations)}")

# Filter test annotations
print("\n5. Filtering test annotations...")
filtered_test_annotations = []
for ann in test_coco['annotations']:
    if ann['category_id'] in old_to_new_id:
        new_ann = ann.copy()
        new_ann['category_id'] = old_to_new_id[ann['category_id']]
        filtered_test_annotations.append(new_ann)

# Find valid test images
valid_test_image_ids = set(ann['image_id'] for ann in filtered_test_annotations)

# Filter test images
filtered_test_images = [img for img in test_coco['images'] if img['id'] in valid_test_image_ids]

print(f"   Original test images: {len(test_coco['images'])}")
print(f"   Filtered test images: {len(filtered_test_images)}")
print(f"   Original annotations: {len(test_coco['annotations'])}")
print(f"   Filtered annotations: {len(filtered_test_annotations)}")

# Create new COCO files
print("\n6. Saving filtered COCO files...")

filtered_train_coco = {
    "info": train_coco.get("info", {}),
    "licenses": train_coco.get("licenses", []),
    "images": filtered_train_images,
    "annotations": filtered_train_annotations,
    "categories": new_categories
}

filtered_test_coco = {
    "info": test_coco.get("info", {}),
    "licenses": test_coco.get("licenses", []),
    "images": filtered_test_images,
    "annotations": filtered_test_annotations,
    "categories": new_categories
}

# Save the files
with open(TRAIN_JSON_OUT, 'w') as f:
    json.dump(filtered_train_coco, f, indent=2)

with open(TEST_JSON_OUT, 'w') as f:
    json.dump(filtered_test_coco, f, indent=2)

print(f"   ✓ Saved: {TRAIN_JSON_OUT}")
print(f"   ✓ Saved: {TEST_JSON_OUT}")

# Save class mapping for reference
import csv
csv_path = os.path.join(OUTPUT_DIR, "class_mapping.csv")
with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['new_id', 'old_id', 'class_name', 'instance_count'])
    for new_id, old_id in enumerate(top50_class_ids):
        writer.writerow([new_id, old_id, class_names[old_id], class_counts[old_id]])

print(f"   ✓ Saved class mapping: {csv_path}")

print("\n" + "=" * 70)
print("✅ STEP 1 COMPLETED SUCCESSFULLY!")
print("=" * 70)
print(f"\n📁 Filtered dataset saved to: {OUTPUT_DIR}")
print(f"\n🔜 NEXT STEP: Run the conversion script to split train/val and convert to YOLO format")