import json
import os

def save_summary(data, filename, summary_dir):
    os.makedirs(summary_dir, exist_ok=True)
    summary_path = os.path.join(summary_dir, filename)
    with open(summary_path, "w") as f:
        json.dump(data, f, indent=2)
