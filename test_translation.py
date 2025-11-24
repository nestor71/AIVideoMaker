#!/usr/bin/env python3
"""
Script di Test per Traduzione Video
====================================
Testa l'importazione e i metodi base del modulo video_translator

Uso:
    python test_translation.py
"""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test import di tutte le dipendenze"""
    print("=" * 60)
    print("TEST 1: Verifica Import Moduli")
    print("=" * 60)

    errors = []

    # Test import moduli base
    try:
        import video_translator
        print("✅ video_translator - OK")
    except ImportError as e:
        print(f"❌ video_translator - ERRORE: {e}")
        errors.append(("video_translator", str(e)))

    # Test import Whisper
    try:
        import whisper
        print("✅ openai-whisper - OK")
    except ImportError as e:
        print(f"⚠️  openai-whisper - NON INSTALLATO (necessario per trascrizione)")
        errors.append(("whisper", str(e)))

    # Test import googletrans
    try:
        from googletrans import Translator
        print("✅ googletrans - OK")
    except ImportError as e:
        print(f"⚠️  googletrans - NON INSTALLATO (necessario per traduzione)")
        errors.append(("googletrans", str(e)))

    # Test import gTTS
    try:
        from gtts import gTTS
        print("✅ gTTS - OK")
    except ImportError as e:
        print(f"⚠️  gTTS - NON INSTALLATO (necessario per sintesi vocale)")
        errors.append(("gTTS", str(e)))

    # Test FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ ffmpeg - OK")
        else:
            print("❌ ffmpeg - ERRORE: non funziona correttamente")
            errors.append(("ffmpeg", "non funziona"))
    except FileNotFoundError:
        print("❌ ffmpeg - NON INSTALLATO (necessario per elaborazione video)")
        errors.append(("ffmpeg", "non trovato"))
    except Exception as e:
        print(f"❌ ffmpeg - ERRORE: {e}")
        errors.append(("ffmpeg", str(e)))

    print()
    return errors

def test_translator_class():
    """Test istanziazione classe VideoTranslator"""
    print("=" * 60)
    print("TEST 2: Verifica Classe VideoTranslator")
    print("=" * 60)

    try:
        from video_translator import VideoTranslator

        translator = VideoTranslator()
        print("✅ VideoTranslator istanziata correttamente")

        # Test lingue supportate
        print(f"✅ Lingue supportate: {len(translator.supported_languages)}")
        for code, name in list(translator.supported_languages.items())[:3]:
            print(f"   - {code}: {name}")
        print("   ... (altre lingue disponibili)")

        print()
        return True

    except Exception as e:
        print(f"❌ Errore istanziazione VideoTranslator: {e}")
        print()
        return False

def test_fastapi_endpoints():
    """Test che gli endpoint FastAPI siano definiti"""
    print("=" * 60)
    print("TEST 3: Verifica Endpoint FastAPI")
    print("=" * 60)

    try:
        # Import app senza avviarla
        import app as app_module

        # Controlla che gli endpoint esistano
        routes = app_module.app.routes
        translation_routes = [r for r in routes if 'translation' in str(r.path)]

        if len(translation_routes) > 0:
            print(f"✅ Trovati {len(translation_routes)} endpoint di traduzione:")
            for route in translation_routes:
                print(f"   - {route.path}")
            print()
            return True
        else:
            print("❌ Nessun endpoint di traduzione trovato")
            print()
            return False

    except Exception as e:
        print(f"❌ Errore verifica endpoint: {e}")
        print()
        return False

def main():
    """Esegue tutti i test"""
    print("\n" + "=" * 60)
    print("🧪 TEST FUNZIONALITÀ TRADUZIONE VIDEO")
    print("=" * 60 + "\n")

    # Test 1: Import
    errors = test_imports()

    # Test 2: Classe
    class_ok = test_translator_class()

    # Test 3: Endpoint
    endpoints_ok = test_fastapi_endpoints()

    # Riepilogo
    print("=" * 60)
    print("📊 RIEPILOGO TEST")
    print("=" * 60)

    if len(errors) == 0 and class_ok and endpoints_ok:
        print("✅ TUTTI I TEST SUPERATI!")
        print("\nPuoi avviare il server con:")
        print("  python app.py")
        print("\nPoi accedi a: http://localhost:8000")
        print("E vai alla tab 'Traduzione Audio'")
        return 0
    else:
        print("⚠️  ALCUNI TEST FALLITI\n")

        if len(errors) > 0:
            print("Dipendenze mancanti:")
            for module, error in errors:
                print(f"  - {module}: {error}")
            print("\nInstalla le dipendenze mancanti con:")
            print("  pip install -r requirements.txt")
            print("  brew install ffmpeg  # macOS")

        if not class_ok:
            print("\n⚠️  Problema con VideoTranslator class")

        if not endpoints_ok:
            print("\n⚠️  Problema con endpoint FastAPI")

        return 1

if __name__ == "__main__":
    sys.exit(main())
