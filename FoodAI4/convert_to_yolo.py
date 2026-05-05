import json
import os
import shutil
import random
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================
FOODAI4_PATH = r"C:\Users\Grand-PC\Desktop\FoodAI4"

# Input paths (filtered dataset from Step 1)
FILTERED_ANNO_DIR = os.path.join(FOODAI4_PATH, "filtered_dataset", "annotations")
TRAIN_JSON = os.path.join(FILTERED_ANNO_DIR, "train_top50.json")
TEST_JSON = os.path.join(FILTERED_ANNO_DIR, "test_top50.json")

# Original image paths
ORIGINAL_TRAIN_IMAGES = os.path.join(FOODAI4_PATH, "images", "train")
ORIGINAL_TEST_IMAGES = os.path.join(FOODAI4_PATH, "images", "test")

# Output paths for YOLO dataset
YOLO_DATASET_DIR = os.path.join(FOODAI4_PATH, "yolo_dataset")
IMAGES_DIR = os.path.join(YOLO_DATASET_DIR, "images")
LABELS_DIR = os.path.join(YOLO_DATASET_DIR, "labels")

# Create YOLO directory structure
for split in ['train', 'val', 'test']:
    os.makedirs(os.path.join(IMAGES_DIR, split), exist_ok=True)
    os.makedirs(os.path.join(LABELS_DIR, split), exist_ok=True)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

print("=" * 70)
print("STEP 2: CONVERTING TO YOLO FORMAT")
print("=" * 70)

# ============================================================================
# STEP 1: Load filtered annotations
# ============================================================================
print("\n1. Loading filtered annotations...")
with open(TRAIN_JSON, 'r') as f:
    train_coco = json.load(f)

with open(TEST_JSON, 'r') as f:
    test_coco = json.load(f)

print(f"   ✓ Loaded training data: {len(train_coco['images'])} images, {len(train_coco['annotations'])} annotations")
print(f"   ✓ Loaded test data: {len(test_coco['images'])} images, {len(test_coco['annotations'])} annotations")
print(f"   ✓ Number of classes: {len(train_coco['categories'])}")

# ============================================================================
# STEP 2: Split training set into train (80%) and validation (20%)
# ============================================================================
print("\n2. Splitting training set into train (80%) and validation (20%)...")

# Get all image IDs from the filtered training set
train_image_ids = [img['id'] for img in train_coco['images']]

# Split the image IDs (80% train, 20% validation)
train_ids, val_ids = train_test_split(train_image_ids, test_size=0.2, random_state=RANDOM_SEED)

print(f"   Original training images: {len(train_image_ids)}")
print(f"   New training images: {len(train_ids)}")
print(f"   Validation images: {len(val_ids)}")

# Function to filter COCO data based on image IDs
def filter_coco_by_image_ids(coco_data, kept_image_ids):
    """Filter images and annotations to keep only specified image IDs."""
    kept_image_ids_set = set(kept_image_ids)
    
    # Filter images
    filtered_images = [img for img in coco_data['images'] if img['id'] in kept_image_ids_set]
    
    # Filter annotations
    filtered_annotations = [ann for ann in coco_data['annotations'] if ann['image_id'] in kept_image_ids_set]
    
    # Create new COCO dict
    filtered_coco = {
        "info": coco_data.get("info", {}),
        "licenses": coco_data.get("licenses", []),
        "images": filtered_images,
        "annotations": filtered_annotations,
        "categories": coco_data['categories']
    }
    return filtered_coco

# Create separate COCO structures for train and validation
train_coco_split = filter_coco_by_image_ids(train_coco, train_ids)
val_coco_split = filter_coco_by_image_ids(train_coco, val_ids)

print(f"\n   Train split: {len(train_coco_split['images'])} images, {len(train_coco_split['annotations'])} annotations")
print(f"   Val split: {len(val_coco_split['images'])} images, {len(val_coco_split['annotations'])} annotations")

# ============================================================================
# STEP 3: Helper function to convert COCO polygon to YOLO polygon
# ============================================================================
def convert_coco_poly_to_yolo_polygon(polygon, img_width, img_height):
    """
    Convert COCO polygon (absolute coordinates) to YOLO polygon (normalized 0-1).
    
    COCO polygon format: [x1, y1, x2, y2, ...] in absolute pixel coordinates
    YOLO polygon format: [x1_norm, y1_norm, x2_norm, y2_norm, ...] normalized to [0,1]
    """
    yolo_polygon = []
    for i in range(0, len(polygon), 2):
        # Normalize x and y coordinates
        x_norm = polygon[i] / img_width
        y_norm = polygon[i+1] / img_height
        
        # Clamp to [0, 1] to avoid floating point errors
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))
        
        yolo_polygon.extend([x_norm, y_norm])
    
    return yolo_polygon

# ============================================================================
# STEP 4: Process and save each split
# ============================================================================
def process_coco_split(coco_data, source_image_dir, output_images_dir, output_labels_dir, split_name):
    """
    Convert a COCO split to YOLO format and save images + label files.
    """
    print(f"\n3. Processing {split_name} split...")
    
    # Create mapping from image ID to image info
    image_info_map = {img['id']: img for img in coco_data['images']}
    
    # Group annotations by image ID
    annotations_by_image = {}
    for ann in coco_data['annotations']:
        image_id = ann['image_id']
        if image_id not in annotations_by_image:
            annotations_by_image[image_id] = []
        annotations_by_image[image_id].append(ann)
    
    # Statistics
    images_processed = 0
    total_annotations = 0
    
    # Process each image
    for img_id, img_info in tqdm(image_info_map.items(), desc=f"   Converting {split_name} images"):
        img_filename = img_info['file_name']
        img_width = img_info['width']
        img_height = img_info['height']
        
        # 1. Copy image file
        src_img_path = os.path.join(source_image_dir, img_filename)
        dst_img_path = os.path.join(output_images_dir, img_filename)
        
        if not os.path.exists(src_img_path):
            print(f"   ⚠ Warning: Image not found: {src_img_path}")
            continue
        
        shutil.copy2(src_img_path, dst_img_path)
        
        # 2. Create label file (.txt)
        label_filename = os.path.splitext(img_filename)[0] + '.txt'
        label_path = os.path.join(output_labels_dir, label_filename)
        
        # 3. Write all annotations for this image to the label file
        with open(label_path, 'w') as f:
            annotations = annotations_by_image.get(img_id, [])
            for ann in annotations:
                category_id = ann['category_id']  # Already mapped to 0-49
                segmentation = ann['segmentation']
                
                # Handle different segmentation formats
                if not segmentation:
                    continue
                
                # segmentation can be a list of polygons (usually one polygon per instance)
                # For YOLO, we write each polygon as a separate line
                for polygon in segmentation:
                    try:
                        yolo_polygon = convert_coco_poly_to_yolo_polygon(polygon, img_width, img_height)
                        
                        # Format: class_id x1 y1 x2 y2 x3 y3 ...
                        line = f"{category_id} " + " ".join([f"{coord:.6f}" for coord in yolo_polygon])
                        f.write(line + '\n')
                        total_annotations += 1
                    except Exception as e:
                        print(f"   ⚠ Error converting polygon for {img_filename}: {e}")
                        continue
        
        images_processed += 1
    
    print(f"   ✓ {split_name}: {images_processed} images, {total_annotations} annotations converted")
    return images_processed, total_annotations

# ============================================================================
# STEP 5: Process all splits
# ============================================================================
# Process TRAIN split
train_images, train_anns = process_coco_split(
    train_coco_split, ORIGINAL_TRAIN_IMAGES,
    os.path.join(IMAGES_DIR, 'train'), os.path.join(LABELS_DIR, 'train'),
    "TRAIN"
)

# Process VALIDATION split
val_images, val_anns = process_coco_split(
    val_coco_split, ORIGINAL_TRAIN_IMAGES,
    os.path.join(IMAGES_DIR, 'val'), os.path.join(LABELS_DIR, 'val'),
    "VALIDATION"
)

# Process TEST split
test_images, test_anns = process_coco_split(
    test_coco, ORIGINAL_TEST_IMAGES,
    os.path.join(IMAGES_DIR, 'test'), os.path.join(LABELS_DIR, 'test'),
    "TEST"
)

# ============================================================================
# STEP 6: Create dataset.yaml file for YOLO
# ============================================================================
print("\n4. Creating dataset.yaml configuration file...")

# Get class names in order of their ID (0-49)
class_names = [cat['name'] for cat in sorted(train_coco['categories'], key=lambda x: x['id'])]

# Convert Windows path to forward slashes for YAML
yolo_dataset_path = YOLO_DATASET_DIR.replace('\\', '/')

yaml_content = f"""# YOLO Segmentation Dataset Configuration
# Generated from FOODAI4 dataset - Top 50 classes

# Dataset paths
path: {yolo_dataset_path}  # dataset root directory
train: images/train  # train images (relative to 'path')
val: images/val      # validation images (relative to 'path')
test: images/test    # test images (relative to 'path')

# Number of classes
nc: {len(class_names)}

# Class names
names: {class_names}
"""

yaml_path = os.path.join(YOLO_DATASET_DIR, 'dataset.yaml')
with open(yaml_path, 'w', encoding='utf-8') as f:
    f.write(yaml_content)

print(f"   ✓ Saved: {yaml_path}")

# ============================================================================
# STEP 7: Create summary report
# ============================================================================
print("\n" + "=" * 70)
print("✅ STEP 2 COMPLETED SUCCESSFULLY!")
print("=" * 70)

print("\n📊 FINAL DATASET SUMMARY:")
print("-" * 70)
print(f"\nYOLO Dataset location: {YOLO_DATASET_DIR}")
print(f"\nClass distribution:")
print(f"   Total classes: {len(class_names)}")
print(f"   Class IDs: 0 to {len(class_names)-1}")
print(f"\nSplit sizes:")
print(f"   TRAIN:     {train_images} images, {train_anns} annotations")
print(f"   VALIDATION: {val_images} images, {val_anns} annotations")
print(f"   TEST:      {test_images} images, {test_anns} annotations")
print(f"\n   Total:     {train_images + val_images + test_images} images")

# Show first 10 classes
print(f"\nFirst 10 classes (IDs 0-9):")
for i in range(min(10, len(class_names))):
    print(f"   {i}: {class_names[i]}")

print("\n" + "=" * 70)
print("🎉 DATASET READY FOR YOLO TRAINING!")
print("=" * 70)
print(f"\n📁 YOLO dataset saved to: {YOLO_DATASET_DIR}")
print(f"📄 Configuration file: {yaml_path}")
print("\n🔜 NEXT STEP: Train YOLO model using:")
print(f"   yolo segment train data={yaml_path} model=yolov8n-seg.pt epochs=100 imgsz=640")