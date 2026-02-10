# 🌉 VerbaBridge (Backend)

The backend API for **VerbaBridge**, featuring the **Rizzeta Stone Protocol** for linguistic translation.

## 🚀 Features
* **Modular Architecture:** Separation of Logic (`ai.py`), Style (`style.py`), and OCR (`ocr.py`).
* **Rizzeta Stone Integration:** Uses the Blackwell et al. (2025) framework to translate standard English into **Gen Alpha Semantics**.
* **Cultural Context:** Supports *Ah Beng (Penang)* and *Mak Cik (Gossip)* dialects.
* **Smart Caching:** JSON-based caching system for instant responses.

## 🛠️ Setup
1. Clone the repo.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file and add your `GEMINI_API_KEY`.
4. Run server: `uvicorn main:app --reload`

## 📚 API Endpoints
* `POST /process_text` - Translate Slang <-> Standard English.
* `POST /translate_style` - Apply Gen Alpha / Brainrot Style.
* `POST /process_image` - OCR Lens feature.