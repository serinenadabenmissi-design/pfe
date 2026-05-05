# FoodInsSeg Dataset

## Dataset description
FoodInsSeg is the first ingredient-level food instance segmentation dataset in the food segmentation field. This dataset contains a total of 7,118 food images, which have been annotated with 103 categories and 119,048 segmentation masks at ingredient level. For each image, we provide individual masks for food items and label each item with one of the 103 food ingredient categories. The whole dataset offers 119,048 instance masks, in which there are 82,716 for training and 36,332 for testing.


## Dataset structure
Our dataset follows the format of the COCO instance segmentation dataset. It contains the original images as well as annotation files, which are split into training and test sets. 
Here is the dataset structure:

```
FoodInsSeg
  -- images
     |-- train
     |   |-- 00000000.jpg
     |   |-- 00000001.jpg 
     |   |-- ...  
     |-- test
     |   |-- 00000048.jpg
     |   |-- 00000263.jpg
     |   |-- ... 
  -- annotations
     |-- Train.json
     |-- Test.json
```

The test.json and train.json annotation files contain five fields: "info", "licenses", "annotations", "images", and "categories". Specifically, the "annotations" field stores instance mask information in polygon format, including mask id, image id, polygon vertices, etc. The "images" field stores image id, width, height, image name, etc. The "categories" field stores the category id and corresponding category name for each class. For more details on the dataset format, please refer to the official COCO dataset documentation.

```
{
  "info": info,
  "images": [image],
  "annotations": [annotation],
  "licenses": [license],
  "categories":[category]
}

image{
  "id": int,
  "width": int,
  "height": int,
  "file_name": str
}

annotation{
  "id": int,
  "image_id": int,
  "category_id": int,
  "segmentation": [polygon],
  "area": float,
  "bbox": [x,y,width,height],
  "iscrowd": 0,
}

category{
  "id": int,
  "name": str,
}
```

## license
```
CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
```

