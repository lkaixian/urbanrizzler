import json
import io
import base64
import time
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageOps  # Crucial for phone photos
from google.genai import types
from core.client import client
from fastapi.concurrency import run_in_threadpool

# --- OCR PROMPT ---
def GET_OCR_REMIX_PROMPT(target_style):
    return f"""
  You are the VerbaBridge **Optical Linguist**.
  Your task is to extract text from the image and **decode** it using your extensive knowledge of Malaysian dialects, Internet Slang (Gen Z/Alpha), and Kopitiam culture.

  ### 🎯 TARGET STYLE: {target_style}

  ### 🕵️‍♂️ ANALYSIS STEPS:
  1. Identify **MULTIPLE** distinct text regions (e.g., separate menu items, signs).
    For EACH region:
       - Read the text.
       - **Translate/Rewrite** it into **{target_style}**.
       - **Locate** its bounding box (ymin, xmin, ymax, xmax).
  2.  **CLASSIFY CONTEXT:** Is this a **Menu** (Kopitiam/Mamak), a **Meme** (Brainrot), a **Signboard**, or a **Chat Screenshot**?
  3.  **DECODE MEANING (Apply All Linguistic Filters):**
      * **The "Kopitiam Algorithm" (Food & Drink):**
          * **"O"** = Black / No Milk (e.g., Kopi O).
          * **"C"** = Evaporated Milk (e.g., Kopi C).
          * **"Kosong"** = No Sugar / Empty.
          * **"Peng" / "Bing"** = Iced.
          * **"Cham" / "Yuan Yang"** = Coffee + Tea Mix.
          * **"Ikat"** = Takeaway (Tied in a bag).
      * **The "Zoomer/Alpha" Filter (Memes):**
          * **Gen Z:** Cap, Bet, Bussin (Delicious), Sheesh.
          * **Gen Alpha:** Skibidi, Rizz, Gyatt, Fanum Tax, Ohio, Sigma.
          * **Italian Brainrot (2025):** Tung Tung Tung, Ballerina Cappuccina.
      * **The "Dialect" Filter (Local Lingo):**
          * **Hokkien:** "Char Koay Teow", "Cia" (Eat), "Bo Jio" (Didn't invite).
          * **Cantonese:** "Leng Zai" (Handsome/Waiter), "Dap Pau" (Takeaway).
          * **Malay Slang:** "Mata" (Police), "Ayam" (Noob/Prostitute).

### 📝 OUTPUT REQUIREMENTS:
    OUTPUT STRICT JSON with this exact structure:
    {{
      "items": [
        {{
          "original": "Chicken Rice",
          "translated": "Sigma Rice",
          "box_2d": [ymin, xmin, ymax, xmax]
        }},
        {{
          "original": "RM 10.00",
          "translated": "10 Fanum Tax",
          "box_2d": [ymin, xmin, ymax, xmax]
        }}
      ]
    }}
    """

# --- VISUAL HELPER: SMART COLOR SAMPLING ---
def _get_smart_bg_color(img_pil, box):
    """
    Samples the PERIMETER of the box to find the true background color.
    This avoids picking up the white text color in the average.
    """
    try:
        width, height = img_pil.size
        ymin, xmin, ymax, xmax = box
        
        # Convert Normalized to Pixels
        left = int((xmin / 1000) * width)
        top = int((ymin / 1000) * height)
        right = int((xmax / 1000) * width)
        bottom = int((ymax / 1000) * height)

        # Safety Check
        if left >= right or top >= bottom: return (0, 0, 0, 220)

        # Crop the region
        region = img_pil.crop((left, top, right, bottom))
        img_np = np.array(region)

        # Sample the 4 edges (Top, Bottom, Left, Right)
        # We take the median color of the edges to ignore noise/text strokes
        if img_np.ndim == 3 and img_np.shape[0] > 0 and img_np.shape[1] > 0:
            top_edge = img_np[0, :, :]
            bottom_edge = img_np[-1, :, :]
            left_edge = img_np[:, 0, :]
            right_edge = img_np[:, -1, :]

            # Combine all edge pixels
            edges = np.concatenate((top_edge, bottom_edge, left_edge, right_edge), axis=0)
            
            # Calculate Median Color (Robust against outliers)
            median_color = np.median(edges, axis=0).astype(int)
        else:
             median_color = np.median(img_np, axis=(0, 1)).astype(int)
        
        # --- FIX IS HERE ---
        # Ensure we only take the first 3 values (RGB) and add Alpha (255)
        # This prevents creating a 5-tuple (R,G,B,A,255) if the source was already RGBA
        return tuple(median_color[:3]) + (255,)
        
    except:
        return (0, 0, 0, 200) # Fallback to semi-transparent black

def _is_dark_color(color_tuple):
    """Returns True if the background is dark (so we should use White text)"""
    r, g, b = color_tuple[:3]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return brightness < 128

def _process_cloud_sync(image_bytes, target_style):
    print(f"☁️ Processing {target_style} Remix (Gemini 3.0)...")
    
    # 1. LOAD & PREPARE IMAGE
    try:
        original = PIL.Image.open(io.BytesIO(image_bytes))
        # FIX: Handle Phone Rotation (EXIF)
        try:
            img = PIL.ImageOps.exif_transpose(original).convert("RGBA")
        except:
            img = original.convert("RGBA")
        
        # Resize for speed (Critical for Hackathon WiFi)
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024))
            
        width, height = img.size
    except Exception as e:
        return {"error": f"Invalid Image: {str(e)}"}

    prompt = GET_OCR_REMIX_PROMPT(target_style)
    ai_response_text = None

    # 2. CALL GEMINI (Retry Logic)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Note: Gemini 3.0 Preview handles images well now
            response = client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=[img, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            ai_response_text = response.text
            break 
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {e}")
            time.sleep(1)

    if not ai_response_text:
        return {"error": "AI Service Timeout (Google Busy)"}

    # 3. PARSE JSON
    try:
        clean_json = ai_response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        items = data.get("items", []) if isinstance(data, dict) else data
        if not isinstance(items, list): items = []
    except Exception as json_err:
        print(f"JSON Error: {json_err}")
        return {"error": "Failed to parse AI response"}

    # 4. VISUAL EDITING (The Polish)
    try:
        draw = PIL.ImageDraw.Draw(img)
        
        for item in items:
            text = item.get("translated", "")
            box = item.get("box_2d") # [ymin, xmin, ymax, xmax]

            if box and len(box) == 4:
                # Get Coords
                ymin, xmin, ymax, xmax = box
                left = (xmin / 1000) * width
                top = (ymin / 1000) * height
                right = (xmax / 1000) * width
                bottom = (ymax / 1000) * height
                
                box_w = right - left
                box_h = bottom - top

                # A. SMART BACKGROUND (The "Chameleon" Effect)
                bg_color = _get_smart_bg_color(img, box)
                
                # Expand box slightly (padding) to ensure we cover messy edges
                pad_x = 4
                pad_y = 4
                draw.rectangle(
                    [left - pad_x, top - pad_y, right + pad_x, bottom + pad_y], 
                    fill=bg_color
                )

                # B. SMART TEXT COLOR
                text_color = (255, 255, 255, 255) if _is_dark_color(bg_color) else (0, 0, 0, 255)

                # C. CENTERED TEXT
                # Dynamic Font Sizing
                font_size = int(max(14, box_h * 0.75))
                try:
                    font = PIL.ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = PIL.ImageFont.load_default()

                center_x = left + (box_w / 2)
                center_y = top + (box_h / 2)

                # Anchor 'mm' = Middle-Middle alignment
                draw.text(
                    (center_x, center_y), 
                    text, 
                    font=font, 
                    fill=text_color,
                    anchor="mm" 
                )

        # 5. RETURN
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {
            "item_count": len(items),
            "original_text": " | ".join([i.get('original', '') for i in items]),
            "translated_text": " | ".join([i.get('translated', '') for i in items]),
            "remixed_image": f"data:image/png;base64,{img_str}"
        }

    except Exception as draw_err:
        return {"error": f"Drawing Error: {str(draw_err)}"}

async def process_image_remix(image_bytes, target_style="Gen Alpha"):
    return await run_in_threadpool(_process_cloud_sync, image_bytes, target_style)