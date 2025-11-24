#!/usr/bin/env python3
"""
Test Integrazione Chromakey
============================
Script per verificare che l'integrazione del chromakey ottimizzato
sia avvenuta correttamente.

Uso:
    python3 test_chromakey_integration.py
"""

import sys
from pathlib import Path

def test_imports():
    """Test import dei moduli"""
    print("=" * 70)
    print("TEST 1: Verifica Import")
    print("=" * 70)

    try:
        from app.services.chromakey_service import ChromakeyService, ChromakeyParams
        print("✅ ChromakeyService importato correttamente")
    except Exception as e:
        print(f"❌ Errore import ChromakeyService: {e}")
        return False

    try:
        from chromakey import remove_background_and_overlay_timed
        print("✅ chromakey.py importato correttamente")
    except Exception as e:
        print(f"❌ Errore import chromakey.py: {e}")
        return False

    return True


def test_service_uses_optimized():
    """Verifica che il servizio usi la funzione ottimizzata"""
    print()
    print("=" * 70)
    print("TEST 2: Verifica Uso Funzione Ottimizzata")
    print("=" * 70)

    try:
        import inspect
        from app.services.chromakey_service import ChromakeyService

        source = inspect.getsource(ChromakeyService.process)

        if 'remove_background_and_overlay_timed' in source:
            print("✅ ChromakeyService.process() usa remove_background_and_overlay_timed")
            return True
        else:
            print("❌ ChromakeyService.process() NON usa la funzione ottimizzata")
            return False
    except Exception as e:
        print(f"❌ Errore verifica codice: {e}")
        return False


def test_backup_exists():
    """Verifica che i backup esistano"""
    print()
    print("=" * 70)
    print("TEST 3: Verifica Backup")
    print("=" * 70)

    backups = [
        "app/services/chromakey_service.py.backup",
        "app/api/routes/chromakey.py.backup"
    ]

    all_exist = True
    for backup in backups:
        backup_path = Path(backup)
        if backup_path.exists():
            size_kb = backup_path.stat().st_size / 1024
            print(f"✅ {backup} ({size_kb:.1f} KB)")
        else:
            print(f"❌ {backup} non trovato")
            all_exist = False

    return all_exist


def test_parameters():
    """Verifica parametri supportati"""
    print()
    print("=" * 70)
    print("TEST 4: Verifica Parametri")
    print("=" * 70)

    try:
        from app.services.chromakey_service import ChromakeyParams
        from dataclasses import fields

        required_params = [
            'foreground_path', 'background_path', 'output_path',
            'start_time', 'duration', 'audio_mode',
            'position', 'scale', 'opacity',
            'fast_mode', 'gpu_accel',
            'logo_path', 'logo_position', 'logo_scale'
        ]

        # Get dataclass fields
        dataclass_fields = [f.name for f in fields(ChromakeyParams)]

        all_present = True
        for param in required_params:
            if param in dataclass_fields:
                print(f"✅ {param}")
            else:
                print(f"❌ {param} mancante")
                all_present = False

        return all_present
    except Exception as e:
        print(f"❌ Errore verifica parametri: {e}")
        return False


def test_service_initialization():
    """Test inizializzazione servizio"""
    print()
    print("=" * 70)
    print("TEST 5: Inizializzazione Servizio")
    print("=" * 70)

    try:
        from app.services.chromakey_service import ChromakeyService

        service = ChromakeyService()
        print("✅ ChromakeyService inizializzato correttamente")

        # Verifica che abbia il metodo process
        if hasattr(service, 'process'):
            print("✅ Metodo process() presente")
        else:
            print("❌ Metodo process() mancante")
            return False

        return True
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        return False


def main():
    """Esegue tutti i test"""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TEST INTEGRAZIONE CHROMAKEY" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    tests = [
        ("Import Moduli", test_imports),
        ("Funzione Ottimizzata", test_service_uses_optimized),
        ("Backup Files", test_backup_exists),
        ("Parametri", test_parameters),
        ("Inizializzazione", test_service_initialization)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Errore durante test '{name}': {e}")
            results.append((name, False))

    # Riepilogo
    print()
    print("=" * 70)
    print("RIEPILOGO TEST")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Risultato: {passed}/{total} test passati")

    if passed == total:
        print()
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 10 + "✅ INTEGRAZIONE COMPLETATA CON SUCCESSO! ✅" + " " * 12 + "║")
        print("╚" + "=" * 68 + "╝")
        print()
        print("Il chromakey ora usa il modulo ottimizzato chromakey.py")
        print("Puoi testare con video reali usando: python3 prova_chromakey.py")
        return True
    else:
        print()
        print("❌ Alcuni test sono falliti. Verifica i messaggi di errore sopra.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
