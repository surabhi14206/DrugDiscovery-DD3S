"""
Test drug_likeness calculations
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.drug_likeness import get_all_drug_likeness_metrics

smiles = "CCOc1ccccc1C(=O)NC1CC2CCCC(C1)N2Cc1ccc(C)cc1"
print(f"Testing SMILES: {smiles}\n")

try:
    metrics = get_all_drug_likeness_metrics(smiles)
    if metrics:
        print("✓ Metrics calculated successfully!")
        print(f"\nSolubility: {metrics.get('solubility')}")
        print(f"\nLipinski: {metrics.get('lipinski')}")
        print(f"\nVeber: {metrics.get('veber')}")
        print(f"\nGhose: {metrics.get('ghose')}")
        print(f"\nToxicity: {metrics.get('toxicity')}")
    else:
        print("❌ Failed to calculate metrics - returned None")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
