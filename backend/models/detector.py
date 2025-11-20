from ultralytics import YOLO
from PIL import Image
import numpy as np
from io import BytesIO
import os
from utils.config_loader import load_config

# Load config and model once
config = load_config()
model_path = os.path.join("models", "weights", "best.pt")
model = YOLO(model_path)

def detect_defects(image_bytes):
    # Load and preprocess image
    image = Image.open(BytesIO(image_bytes)).convert("L").resize(tuple([256,256]))
    image = Image.merge("RGB", (image, image, image))
    image_array = np.array(image)

    # Run prediction
    results = model.predict(image_array, conf=0.2)
    result = results[0]

    # Annotated image
    result_img = result.plot(line_width=2, font_size=1, font="Arial")
    result_pil = Image.fromarray(result_img, mode="RGB")
    result_pil = result_pil.resize((512, 512), resample=Image.BICUBIC)

    # Save annotated image to raw bytes (PNG format)
    buf = BytesIO()
    result_pil.save(buf, format="PNG")
    result_bytes = buf.getvalue()   # 👈 raw binary instead of base64

    # Detection summary
    summary = []
    for i, box in enumerate(result.boxes):
        cls_id = int(box.cls)
        cls_name = model.names[cls_id]
        conf = float(box.conf)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        summary.append({
            "id": i + 1,
            "class": cls_name,
            "confidence": round(conf, 2),
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        })

    return {
        "result_image_bytes": result_bytes,  # 👈 now returns bytes
        "detections": summary
    }
