import os
import django
import sys

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.models import Molecule
import requests

print("=" * 70)
print("TESTING 3D VISUALIZATION AND DATA ACCURACY")
print("=" * 70)

# Get a sample molecule
molecule = Molecule.objects.first()
if molecule:
    print(f"\n✓ Sample Molecule Found:")
    print(f"  ID: {molecule.id}")
    print(f"  Name: {molecule.name}")
    print(f"  SMILES: {molecule.smiles}")
    print(f"  Gene Target: {molecule.gene_target}")
    print(f"  Is Active: {molecule.is_active}")
    print(f"  Structure File: {molecule.structure_file}")
    print(f"  Toxicity Score: {molecule.toxicity_score}")
    print(f"  Solubility: {molecule.solubility}")
    
    # Test PubChem API for 3D structure
    print(f"\n{'='*70}")
    print("TESTING PUBCHEM API FOR 3D STRUCTURE")
    print("=" * 70)
    
    smiles = molecule.smiles
    # Test with URL encoding
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{requests.utils.quote(smiles)}/SDF"
    print(f"\nURL: {url}")
    
    try:
        response = requests.get(url, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✓ 3D structure retrieved successfully!")
            print(f"  Size: {len(response.text)} characters")
            print(f"  First 200 chars: {response.text[:200]}")
        else:
            print(f"✗ Failed to get 3D structure")
            print(f"  Response: {response.text[:500]}")
            
            # Try alternative: 2D structure
            print(f"\nTrying 2D structure...")
            url_2d = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{requests.utils.quote(smiles)}/PNG"
            response_2d = requests.get(url_2d, timeout=15)
            print(f"  2D Image Status: {response_2d.status_code}")
            if response_2d.status_code == 200:
                print(f"  ✓ 2D structure available ({len(response_2d.content)} bytes)")
            
    except requests.exceptions.Timeout:
        print("✗ Request timeout - PubChem might be slow")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Check if SMILES is valid
    print(f"\n{'='*70}")
    print("VALIDATING SMILES WITH RDKit")
    print("=" * 70)
    
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            print(f"✓ SMILES is valid!")
            print(f"  Formula: {Chem.rdMolDescriptors.CalcMolFormula(mol)}")
            print(f"  MW: {Chem.Descriptors.MolWt(mol):.2f}")
            print(f"  Num Atoms: {mol.GetNumAtoms()}")
        else:
            print(f"✗ SMILES is INVALID - Cannot parse: {smiles}")
    except Exception as e:
        print(f"✗ RDKit error: {e}")
else:
    print("\n✗ No molecules in database!")

print(f"\n{'='*70}")
print("RECOMMENDATION")
print("=" * 70)
print("""
If 3D view is not showing, possible issues:
1. CORS blocking PubChem requests (use browser console to check)
2. Invalid SMILES strings in database
3. JavaScript errors (check browser console: F12)
4. 3Dmol.js library not loading

Quick Fixes:
- Check browser console (F12) for errors
- Verify 3Dmol.js CDN is accessible
- Ensure SMILES strings are valid
""")
