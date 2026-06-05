"""
Quick Test Script for Database Integration
Tests PubChem and ChEMBL fetching with validation
"""
import sys
from molecular_database_fetcher import PubChemFetcher, ChEMBLFetcher, fetch_training_data

def test_pubchem():
    """Test PubChem API"""
    print("=" * 60)
    print("Testing PubChem API")
    print("=" * 60)
    
    print("\nFetching benzene derivatives (C6H6)...")
    compounds = PubChemFetcher.fetch_compounds_by_formula("C6H6", max_results=10)
    
    if compounds:
        print(f"✓ Successfully fetched {len(compounds)} compounds")
        print("\nSample SMILES:")
        for i, comp in enumerate(compounds[:5], 1):
            smiles = comp.get('CanonicalSMILES', 'N/A')
            formula = comp.get('MolecularFormula', 'N/A')
            print(f"  {i}. {smiles} ({formula})")
        return True
    else:
        print("✗ Failed to fetch from PubChem")
        return False

def test_chembl():
    """Test ChEMBL API"""
    print("\n" + "=" * 60)
    print("Testing ChEMBL API")
    print("=" * 60)
    
    print("\nFetching molecules from ChEMBL...")
    molecules = ChEMBLFetcher.fetch_molecules(limit=10)
    
    if molecules:
        print(f"✓ Successfully fetched {len(molecules)} molecules")
        print("\nSample SMILES:")
        for i, mol in enumerate(molecules[:5], 1):
            smiles = mol.get('CanonicalSMILES', 'N/A')
            mol_id = mol.get('CID', 'N/A')
            print(f"  {i}. {smiles} ({mol_id})")
        return True
    else:
        print("✗ Failed to fetch from ChEMBL")
        return False

def test_integrated_fetch():
    """Test integrated fetch with validation"""
    print("\n" + "=" * 60)
    print("Testing Integrated Fetch (PubChem + ChEMBL + RDKit)")
    print("=" * 60)
    
    print("\nFetching 100 molecules from both databases...")
    try:
        smiles_list = fetch_training_data(count=100, source='both', validate=True)
        
        if smiles_list:
            print(f"✓ Successfully fetched and validated {len(smiles_list)} SMILES")
            
            # Show statistics
            lengths = [len(s) for s in smiles_list]
            avg_length = sum(lengths) / len(lengths)
            
            print(f"\nStatistics:")
            print(f"  Total: {len(smiles_list)}")
            print(f"  Avg length: {avg_length:.1f} characters")
            print(f"  Min length: {min(lengths)}")
            print(f"  Max length: {max(lengths)}")
            
            print(f"\nSample SMILES:")
            for i, smiles in enumerate(smiles_list[:10], 1):
                print(f"  {i}. {smiles}")
            
            return True
        else:
            print("✗ No SMILES fetched")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_rdkit_validation():
    """Test RDKit validation"""
    print("\n" + "=" * 60)
    print("Testing RDKit Validation")
    print("=" * 60)
    
    try:
        from rdkit import Chem
        
        test_smiles = [
            "c1ccccc1",  # Benzene (valid)
            "CCO",  # Ethanol (valid)
            "C1CCCCC1",  # Cyclohexane (valid)
            "invalid",  # Invalid
            "CC(C)CC",  # Isopentane (valid)
        ]
        
        print("\nValidating test SMILES:")
        valid_count = 0
        
        for smiles in test_smiles:
            mol = Chem.MolFromSmiles(smiles)
            if mol is not None:
                canonical = Chem.MolToSmiles(mol)
                print(f"  ✓ {smiles} → {canonical}")
                valid_count += 1
            else:
                print(f"  ✗ {smiles} (invalid)")
        
        print(f"\nValidation rate: {valid_count}/{len(test_smiles)}")
        return True
        
    except ImportError:
        print("✗ RDKit not installed")
        print("  Install with: pip install rdkit")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MOLECULAR DATABASE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test PubChem
    results.append(("PubChem", test_pubchem()))
    
    # Test ChEMBL
    results.append(("ChEMBL", test_chembl()))
    
    # Test RDKit
    results.append(("RDKit", test_rdkit_validation()))
    
    # Test integrated fetch
    results.append(("Integrated Fetch", test_integrated_fetch()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n✓ All tests passed! Ready to train enhanced model.")
        print("\nNext steps:")
        print("  1. Run: python ml_smiles_generator_enhanced.py")
        print("  2. Choose option 1 (PubChem + ChEMBL)")
        print("  3. Wait for training to complete")
        print("  4. Test 'Generate ML SMILES' button in web interface")
    else:
        print("\n⚠ Some tests failed. Check error messages above.")
        if not results[0][1] and not results[1][1]:
            print("\n  Possible issues:")
            print("    - No internet connection")
            print("    - API rate limiting")
            print("    - Firewall blocking requests")
            print("\n  You can still use local JSON files for training.")
    
    return total_passed == len(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
