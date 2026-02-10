import json
import io
import PIL.Image
from google.genai import types
from core.client import client  # Import shared client

OCR_PROMPT = """
Look at this image.
1. Extract ALL text found in the image.
2. If it's a Menu/Signboard, translate the items into **English** and **Standard Malay**.
3. If it contains Dialect/Slang (e.g. "Char Koay Teow", "Kopi O"), explain what it is.

OUTPUT STRICT JSON:
{{
  "detected_text": "...",
  "translations": [
    {{ "original": "Kopi O", "meaning": "Black Coffee with Sugar" }},
    {{ "original": "Cham", "meaning": "Coffee + Tea Mix" }}
  ]
}}
"""

def process_image(image_bytes):
    print(f"📷 Processing Image...")
    try:
        # Convert bytes to PIL Image
        img = PIL.Image.open(io.BytesIO(image_bytes))
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, OCR_PROMPT],  # Image + Text Prompt
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return {"error": str(e)}