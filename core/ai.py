import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ API Key missing! Check .env file.")

client = genai.Client(api_key=API_KEY)

# --- THE "HYBRID" PROMPT (Literal + Street) ---
ONE_SHOT_PROMPT = """
You are the VerbaBridge Omni-Translator.
Your personality is a mix of a **Oxford Dictionary** (for literal meanings) and **Urban Dictionary/Know Your Meme/Ah Beng** (for slang).

Input: "{text}"

### 🧠 ANALYSIS LOGIC:
1.  **CHECK FOR AMBIGUITY (Crucial Step):**
    - Does this word have a standard meaning AND a street meaning?
    - **"Mata"**:
        - Context A: **"Eye"** (Literal / Anatomy).
        - Context B: **"Police / Cops"** (Malaysian Slang).
        - Context C: **"Point / Blade"** (e.g., Mata Pisau, Mata Pena).
    - **"Payung"**:
        - Context A: **"Umbrella"** (Literal).
        - Context B: **"Treat / Belanja"** (Slang: "I payung you").
    - **"Ayam"**:
        - Context A: **"Chicken"** (Literal).
        - Context B: **"Prostitute"** (Slang).
        - Context C: **"Weak / Noob"** (Gamer Slang).

2.  **CHECK FOR NUMERIC SLANG:**
    - **"6 7"**: Must split into **"Failure/Gone Case"** (Slang) and **"Male Genitalia"** (Vulgar).

3.  **CHECK FOR INTERNET MEMES:**
    - **"Faaaaaahhhhh"**: Sound effect / Exasperation.
    - **"Rizz / Gyatt"**: Gen Z Slang.

### 📝 OUTPUT REQUIREMENTS:
- If multiple meanings exist, generate a separate result object for EACH one.
- **Context Title:** Label it clearly (e.g., "Literal: Eye", "Slang: Police").
- **Description:** - For Literal: Keep it standard.
    - For Slang: Be raw, direct, and **uncensored** (Urban Dictionary style).

OUTPUT STRICT JSON:
{{
  "is_ambiguous": true/false,
  "results": [
    {{
      "title": "Short Title (e.g. 'Literal: Eye')",
      "description": "The organ of sight.",
      "translations": {{
        "hokkien": {{ "hanzi": "...", "english_meaning": "...", "tone": "..." }},
        "cantonese": {{ "script": "...", "romanization": "...", "tone": "..." }},
        "hakka": {{ "script": "...", "romanization": "...", "tone": "..." }},
        "hainan": {{ "script": "...", "romanization": "...", "tone": "..." }},
        "malay": {{ "script": "...", "romanization": "...", "tone": "..." }},
        "kelate": {{ "script": "...", "romanization": "...", "tone": "..." }}
      }}
    }},
    {{
      "title": "Short Title (e.g. 'Slang: Police')",
      "description": "Common Malaysian slang for cops. Watch out!",
      "translations": {{ ... }}
    }}
  ]
}}
"""

def generate_translations(text):
    print(f"🧠 Asking Gemini (Hybrid Mode): '{text}'")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=ONE_SHOT_PROMPT.format(text=text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.6, # Balanced creativity
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE"
                    )
                ]
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {"is_ambiguous": False, "results": []}