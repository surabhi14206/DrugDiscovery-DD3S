"""
Diagnostic script to check RDKit 2D rendering backends.
Run this to see which drawing backend is available on your system.

Usage:
    python check_rdkit_backend.py
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("RDKit 2D Rendering Backend Diagnostic")
print("=" * 60)

# Test 1: Check RDKit installation
print("\n[1] Checking RDKit installation...")
try:
    from rdkit import Chem
    from rdkit import __version__ as rdkit_version
    print(f"✅ RDKit installed: v{rdkit_version}")
except ImportError as e:
    print(f"❌ RDKit not installed: {e}")
    print("\nInstall RDKit:")
    print("  pip install rdkit")
    print("  OR")
    print("  conda install -c conda-forge rdkit")
    sys.exit(1)

# Test 2: Check rdMolDraw2D backend
print("\n[2] Checking rdMolDraw2D backend (modern, high quality)...")
try:
    from rdkit.Chem.Draw import rdMolDraw2D
    print("✅ rdMolDraw2D available")
    backend_rdMolDraw2D = True
except (ImportError, OSError) as e:
    print(f"❌ rdMolDraw2D blocked: {e}")
    print("   → Windows Defender may be blocking rdMolDraw2D.dll")
    print("   → See FIX_WINDOWS_2D_RENDERING.md for solutions")
    backend_rdMolDraw2D = False

# Test 3: Check Cairo backend
print("\n[3] Checking Cairo backend (fallback)...")
try:
    from rdkit.Chem.Draw import MolDraw2DCairo
    print("✅ Cairo backend available")
    backend_cairo = True
except (ImportError, OSError) as e:
    print(f"❌ Cairo not available: {e}")
    print("   → Install with: conda install -c conda-forge cairo")
    backend_cairo = False

# Test 4: Check PIL backend (basic)
print("\n[4] Checking PIL backend (legacy, always works)...")
try:
    from rdkit.Chem import Draw
    from PIL import Image
    print("✅ PIL backend available")
    backend_pil = True
except ImportError as e:
    print(f"❌ PIL not available: {e}")
    print("   → Install with: pip install Pillow")
    backend_pil = False

# Test 5: Actual rendering test
print("\n[5] Testing actual 2D rendering...")
if backend_pil:
    try:
        from rdkit.Chem import Draw
        mol = Chem.MolFromSmiles('CC(=O)OC1=CC=CC=C1C(=O)O')  # Aspirin
        img = Draw.MolToImage(mol, size=(300, 300))
        print("✅ Successfully rendered test molecule (Aspirin)")
        print(f"   Image type: {type(img)}")
        print(f"   Image size: {img.size}")
    except Exception as e:
        print(f"❌ Rendering failed: {e}")
else:
    print("⚠️  Cannot test - no drawing backend available")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

available_backends = []
if backend_rdMolDraw2D:
    available_backends.append("rdMolDraw2D (preferred)")
if backend_cairo:
    available_backends.append("Cairo (good)")
if backend_pil:
    available_backends.append("PIL (basic)")

if available_backends:
    print(f"✅ Available backends: {', '.join(available_backends)}")
    print(f"\n📌 Your DD3S will use: {available_backends[0]}")
else:
    print("❌ No drawing backends available!")
    print("\nRecommended fixes:")
    print("1. Add Windows Security exclusion for .venv folder")
    print("2. Reinstall RDKit: pip install rdkit --no-cache-dir")
    print("3. Try older version: pip install rdkit==2024.03.6")
    print("\nSee FIX_WINDOWS_2D_RENDERING.md for detailed instructions.")

# System info
print("\n" + "=" * 60)
print("SYSTEM INFO")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")

import platform
print(f"OS: {platform.system()} {platform.release()}")

print("\n" + "=" * 60)
print("If you see ❌ for rdMolDraw2D, follow FIX_WINDOWS_2D_RENDERING.md")
print("=" * 60)
