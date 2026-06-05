"""
Test molecular formula generation for disconnected components
"""
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from collections import Counter

def test_disconnected_carbons():
    """Test case: 5 carbons, only 2 are bonded"""
    
    # Create molecule
    em = Chem.EditableMol(Chem.Mol())
    
    # Add 5 carbon atoms
    for i in range(5):
        em.AddAtom(Chem.Atom('C'))
    
    # Add only 1 bond connecting first 2 carbons
    em.AddBond(0, 1, Chem.BondType.SINGLE)
    
    mol = em.GetMol()
    
    print("Testing 5 carbons with 1 bond...")
    print(f"Total atoms: {mol.GetNumAtoms()}")
    print(f"Total bonds: {mol.GetNumBonds()}")
    
    # Split into fragments
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=False)
    print(f"\nNumber of disconnected fragments: {len(frags)}")
    
    # Analyze each fragment
    for idx, frag in enumerate(frags, 1):
        print(f"\n--- Fragment {idx} ---")
        print(f"Atoms: {frag.GetNumAtoms()}")
        print(f"Bonds: {frag.GetNumBonds()}")
        
        try:
            # Try with hydrogens
            Chem.SanitizeMol(frag)
            frag_h = Chem.AddHs(frag)
            smiles = Chem.MolToSmiles(frag_h, canonical=True)
            formula = rdMolDescriptors.CalcMolFormula(frag_h)
            print(f"SMILES: {smiles}")
            print(f"Formula: {formula}")
        except Exception as e:
            # Fallback without hydrogens
            print(f"Sanitization failed: {e}")
            frag.UpdatePropertyCache(strict=False)
            smiles = Chem.MolToSmiles(frag, canonical=False)
            counts = Counter(a.GetSymbol() for a in frag.GetAtoms())
            formula = "".join(f"{el}{cnt}" if cnt > 1 else el for el, cnt in sorted(counts.items()))
            print(f"SMILES (no H): {smiles}")
            print(f"Formula (explicit): {formula}")
    
    # Show expected output
    print("\n" + "="*50)
    print("EXPECTED OUTPUT:")
    print("Formula: C2H6 + CH4 + CH4 + CH4")
    print("Or simplified: C2H6 + 3×CH4")
    print("="*50)

if __name__ == "__main__":
    test_disconnected_carbons()
