import os
import json
import hashlib
from core.client import CACHE_DIR

class FileSystemCache:
    def __init__(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            print(f"📁 Created cache directory: {CACHE_DIR}/")

    def _get_hash(self, text):
        clean_text = text.strip().lower()
        return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

    def get(self, text):
        file_hash = self._get_hash(text)
        file_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ Cache Read Error: {e}")
                return None
        return None

    def set(self, text, data):
        file_hash = self._get_hash(text)
        file_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠ Cache Write Error: {e}")
