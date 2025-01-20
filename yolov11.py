from ultralytics import YOLO

#model = YOLO("yolo11n.yaml")

# Load a model
model = YOLO("yolo11n.pt")  # load an official model
#model = YOLO("path/to/best.pt")  # load a custom model

# Predict with the model
results = model("/mnt/Data/bosong/sam2/gaze/00109.jpg")  # predict on an image

# Process results list
for result in results:
    boxes = result.boxes  # Boxes object for bounding box outputs
    masks = result.masks  # Masks object for segmentation masks outputs
    keypoints = result.keypoints  # Keypoints object for pose outputs
    probs = result.probs  # Probs object for classification outputs
    obb = result.obb  # Oriented boxes object for OBB outputs
    result.show()  # display to screen
    result.save(filename="result0109.jpg")  # save to disk