import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# --- MODULAR IMPORTS ---
from core.cache import FileSystemCache
from core.ai import generate_translations      # The Main Translation Logic
from core.style import translate_style         # The "Vibe" Translator
from core.ocr import process_image             # The "Lens" Feature
from core.utils import get_hokkien_romanization # The Penang Patcher

# --- APP SETUP ---
app = FastAPI(title="VerbaBridge Modular", version="10.0")
cache = FileSystemCache()

# --- DATA MODELS ---
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
        return "<h1 style='color:red'>Error: static/index.html not found!</h1>"

# 1. CORE TRANSLATION ENDPOINT (With Caching)
@app.post("/process_text")
async def process_text(data: UserInput):
    print(f"📩 Input: '{data.text}'")

    # STEP 1: CHECK CACHE (Speed Layer)
    cached_data = cache.get(data.text)
    if cached_data:
        print("⚡ CACHE HIT")
        # Handle backward compatibility for older cache files
        is_ambig = cached_data.get("is_ambiguous", len(cached_data.get("results", [])) > 1)
        
        return {
            "status": "success", 
            "source": "cache", 
            "is_ambiguous": is_ambig,
            "results": cached_data["results"]
        }

    # STEP 2: ASK AI (Compute Layer)
    ai_data = generate_translations(data.text)
    
    if not ai_data.get("results"):
        return {"status": "error", "message": "AI generation failed"}

    # STEP 3: APPLY HOKKIEN PATCH (Logic Layer)
    # We fix the spelling BEFORE saving to cache, so we don't have to fix it again later.
    final_results = ai_data["results"]
    for res in final_results:
        try:
            hanzi = res["translations"]["hokkien"]["hanzi"]
            res["translations"]["hokkien"]["romanization"] = get_hokkien_romanization(hanzi)
        except KeyError:
            pass 

    # STEP 4: SAVE TO CACHE (Persistence Layer)
    # We save the entire object including the 'is_ambiguous' flag
    cache.set(data.text, ai_data) 

    return {
        "status": "success", 
        "source": "gemini", 
        "is_ambiguous": ai_data["is_ambiguous"],
        "results": final_results
    }

# 2. STYLE TRANSFER ENDPOINT (New Feature)
@app.post("/translate_style")
async def api_translate_style(data: StyleInput):
    """
    Converts text into Gen Alpha, Ah Beng, or Corporate slang.
    Note: We generally DON'T cache this because style transfer is highly variable,
    but you could add cache here if you wanted.
    """
    return translate_style(data.text, data.style)

# 3. OCR / LENS ENDPOINT (New Feature)
@app.post("/process_image")
async def api_process_image(file: UploadFile = File(...)):
    """
    Reads a menu or signboard and translates it.
    """
    image_bytes = await file.read()
    return process_image(image_bytes)