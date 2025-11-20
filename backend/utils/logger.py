from datetime import datetime
import os

def log_audit(message, log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now().isoformat()
    with open(log_path, "a") as f:
        f.write(f"{timestamp} - {message}\n")
