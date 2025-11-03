# export_util.py
import base64

def save_b64_to_file(b64str, filepath):
    data = base64.b64decode(b64str)
    with open(filepath, 'wb') as f:
        f.write(data)
