import os
import json
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# --- MODULAR IMPORTS ---
from core.cache import FileSystemCache
from core.ai import generate_translations       # The Main Logic
from core.style import translate_style          # The "Brainrot" Engine
from core.ocr import process_image_remix       # The "Visual Remix" Engine
from core.utils import get_hokkien_romanization # The Penang Patcher

# --- SETUP ---
load_dotenv()
app = FastAPI(title="VerbaBridge Backend", version="2.0.0")
cache = FileSystemCache()

# --- DATA MODELS (Input Validation) ---
class UserInput(BaseModel):
    text: str

class StyleInput(BaseModel):
    text: str
    style: str  # e.g., "Gen Alpha", "Ah Beng"

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serves the Frontend Dashboard"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1 style='color:red; font-family:sans-serif'>Error: static/index.html not found!</h1>"

# 1. CORE TRANSLATION (Text -> Culture)
@app.post("/process_text")
async def process_text(data: UserInput):
    print(f"📩 Processing Text: '{data.text}'")

    # A. Check Cache (Speed Layer)
    cached_data = cache.get(data.text)
    if cached_data:
        print("⚡ CACHE HIT")
        return {
            "status": "success", 
            "source": "cache", 
            "is_ambiguous": cached_data.get("is_ambiguous", False),
            "results": cached_data.get("results", [])
        }

    # B. Ask AI (Intelligence Layer)
    ai_data = generate_translations(data.text)
    
    if not ai_data or not ai_data.get("results"):
        return {"status": "error", "message": "AI generation failed"}

    # C. Apply Penang Hokkien Patch (Logic Layer)
    # This fixes the romanization using your 'Taibun' utility
    for res in ai_data["results"]:
        try:
            raw_hanzi = res["translations"]["hokkien"]["hanzi"]
            # Convert Hanzi -> Penang Romanization
            res["translations"]["hokkien"]["romanization"] = get_hokkien_romanization(raw_hanzi)
        except KeyError:
            pass 

    # D. Save to Cache (Persistence Layer)
    cache.set(data.text, ai_data) 

    return {
        "status": "success", 
        "source": "gemini", 
        "is_ambiguous": ai_data.get("is_ambiguous", False),
        "results": ai_data["results"]
    }

# 2. STYLE TRANSFER (Text -> Slang)
@app.post("/translate_style")
async def api_translate_style(data: StyleInput):
    """
    Converts standard text into a specific persona (Gen Alpha, Ah Beng, etc.)
    """
    print(f"🎭 Applying Style [{data.style}] to: '{data.text}'")
    return translate_style(data.text, data.style)

# 3. VISUAL REMIX (Image -> Translated Overlay)
@app.post("/process_image")
async def api_process_image(
    file: UploadFile = File(...), 
    style: str = Form("Gen Alpha") # Default style if not provided
):
    """
    Takes an image, translates the text inside it, and overlays the translation.
    """
    try:
        # Read the uploaded file bytes
        image_bytes = await file.read()
        
        # Send to core/ocr.py for processing
        # This function handles Gemini Analysis + Pillow Drawing
        result = await process_image_remix(image_bytes, target_style=style)
        
        if "error" in result:
             return JSONResponse(result, status_code=500)

        return result

    except Exception as e:
        print(f"❌ Server Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)