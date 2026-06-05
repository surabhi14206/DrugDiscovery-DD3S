"""
Drug-Likeness and Toxicity Prediction Module
Implements Lipinski, Veber, Ghose filters, ESOL solubility, and toxicity alerts
Based on QSAR models and structural heuristics for drug discovery
"""
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors
except ImportError:
    Chem = None
    Descriptors = None
    Crippen = None
    Lipinski = None
    rdMolDescriptors = None
import logging

logger = logging.getLogger(__name__)


def predict_esol_solubility(smiles):
    """
    Predict aqueous solubility using ESOL (Estimated SOLubility) equation by Delaney (2004)
    
    Formula: logS ≈ 0.16 - 0.63×cLogP - 0.0062×MW + 0.066×RB - 0.74×AP
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: {
            'logS': float,  # Predicted logS (mol/L)
            'solubility_class': str,  # 'Highly Soluble', 'Soluble', 'Moderately Soluble', 'Poorly Soluble', 'Insoluble'
            'interpretation': str
        }
    """
    if Chem is None or Descriptors is None or Crippen is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        # Calculate descriptors
        mw = Descriptors.MolWt(mol)
        clogp = Crippen.MolLogP(mol)
        rb = Descriptors.NumRotatableBonds(mol)
        aromatic_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
        heavy_atoms = Descriptors.HeavyAtomCount(mol)
        ap = aromatic_atoms / heavy_atoms if heavy_atoms > 0 else 0
        
        # ESOL equation
        logS = 0.16 - 0.63 * clogp - 0.0062 * mw + 0.066 * rb - 0.74 * ap
        
        # Classify solubility
        if logS >= -2:
            sol_class = "Highly Soluble"
            interpretation = "Excellent aqueous solubility (>0.01 M). Ideal for formulation."
        elif logS >= -4:
            sol_class = "Soluble"
            interpretation = "Good solubility (0.0001-0.01 M). Suitable for oral drugs."
        elif logS >= -6:
            sol_class = "Moderately Soluble"
            interpretation = "Moderate solubility (0.000001-0.0001 M). May need formulation strategies."
        elif logS >= -8:
            sol_class = "Poorly Soluble"
            interpretation = "Low solubility (<0.000001 M). Significant formulation challenges."
        else:
            sol_class = "Insoluble"
            interpretation = "Very poor solubility. Not suitable for oral delivery without major modifications."
        
        return {
            'logS': round(logS, 2),
            'solubility_class': sol_class,
            'interpretation': interpretation,
            'descriptors': {
                'cLogP': round(clogp, 2),
                'MW': round(mw, 1),
                'Rotatable_Bonds': rb,
                'Aromatic_Proportion': round(ap, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating ESOL: {e}")
        return None


def check_lipinski_rule_of_five(smiles):
    """
    Check Lipinski's Rule of Five for oral drug-likeness
    
    Criteria:
    - MW ≤ 500 Da
    - cLogP ≤ 5
    - H-bond donors ≤ 5
    - H-bond acceptors ≤ 10
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: {
            'compliant': bool,  # True if ≤1 violation
            'violations': int,
            'details': dict,
            'interpretation': str
        }
    """
    if Chem is None or Descriptors is None or Crippen is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        mw = Descriptors.MolWt(mol)
        clogp = Crippen.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)
        
        violations = []
        if mw > 500:
            violations.append(f"MW too high ({mw:.1f} > 500)")
        if clogp > 5:
            violations.append(f"cLogP too high ({clogp:.2f} > 5)")
        if hbd > 5:
            violations.append(f"H-donors too many ({hbd} > 5)")
        if hba > 10:
            violations.append(f"H-acceptors too many ({hba} > 10)")
        
        num_violations = len(violations)
        compliant = num_violations <= 1
        
        if compliant:
            interpretation = "✅ Lipinski compliant - Good oral bioavailability expected"
        else:
            interpretation = f"⚠️ {num_violations} Lipinski violations - Poor oral absorption likely"
        
        return {
            'compliant': compliant,
            'violations': num_violations,
            'violation_details': violations,
            'details': {
                'MW': round(mw, 1),
                'cLogP': round(clogp, 2),
                'H_Bond_Donors': hbd,
                'H_Bond_Acceptors': hba
            },
            'interpretation': interpretation
        }
    except Exception as e:
        logger.error(f"Error checking Lipinski: {e}")
        return None


def check_veber_rule(smiles):
    """
    Check Veber's rule for drug absorption and oral bioavailability
    
    Criteria:
    - Rotatable bonds ≤ 10
    - TPSA ≤ 140 Ų
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: {
            'compliant': bool,
            'details': dict,
            'interpretation': str
        }
    """
    if Chem is None or Descriptors is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        nrot = Descriptors.NumRotatableBonds(mol)
        tpsa = rdMolDescriptors.CalcTPSA(mol)
        
        violations = []
        if nrot > 10:
            violations.append(f"Too flexible ({nrot} > 10 rotatable bonds)")
        if tpsa > 140:
            violations.append(f"Too polar (TPSA {tpsa:.1f} > 140)")
        
        compliant = len(violations) == 0
        
        if compliant:
            interpretation = "✅ Veber compliant - Good membrane permeability expected"
        else:
            interpretation = f"⚠️ Veber violations: {'; '.join(violations)}"
        
        return {
            'compliant': compliant,
            'violations': len(violations),
            'violation_details': violations,
            'details': {
                'Rotatable_Bonds': nrot,
                'TPSA': round(tpsa, 1)
            },
            'interpretation': interpretation
        }
    except Exception as e:
        logger.error(f"Error checking Veber: {e}")
        return None


def check_ghose_filter(smiles):
    """
    Check Ghose drug-likeness filter
    
    Criteria:
    - MW: 160-480 Da
    - cLogP: -0.4 to 5.6
    - Molar Refractivity: 40-130
    - Heavy atoms: 20-70
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: {
            'compliant': bool,
            'details': dict,
            'interpretation': str
        }
    """
    if Chem is None or Descriptors is None or Crippen is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        mw = Descriptors.MolWt(mol)
        clogp = Crippen.MolLogP(mol)
        mr = Descriptors.MolMR(mol)
        num_atoms = mol.GetNumHeavyAtoms()
        
        violations = []
        if not (160 <= mw <= 480):
            violations.append(f"MW out of range ({mw:.1f} not in 160-480)")
        if not (-0.4 <= clogp <= 5.6):
            violations.append(f"cLogP out of range ({clogp:.2f} not in -0.4 to 5.6)")
        if not (40 <= mr <= 130):
            violations.append(f"Molar Refractivity out of range ({mr:.1f} not in 40-130)")
        if not (20 <= num_atoms <= 70):
            violations.append(f"Heavy atoms out of range ({num_atoms} not in 20-70)")
        
        compliant = len(violations) == 0
        
        if compliant:
            interpretation = "✅ Ghose filter passed - Falls within typical drug-like chemical space"
        else:
            interpretation = f"⚠️ Ghose violations: {'; '.join(violations)}"
        
        return {
            'compliant': compliant,
            'violations': len(violations),
            'violation_details': violations,
            'details': {
                'MW': round(mw, 1),
                'cLogP': round(clogp, 2),
                'Molar_Refractivity': round(mr, 1),
                'Heavy_Atoms': num_atoms
            },
            'interpretation': interpretation
        }
    except Exception as e:
        logger.error(f"Error checking Ghose: {e}")
        return None


def check_toxicity_alerts(smiles):
    """
    Check for structural alerts (toxicophores) linked to toxicity
    
    Based on literature (Ashby-Tennant, Toxtree, ToxAlerts)
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: {
            'alerts_found': list,
            'risk_level': str,  # 'High', 'Medium', 'Low'
            'interpretation': str
        }
    """
    # Toxicity alerts with SMARTS patterns
    alerts_db = {
        'Aromatic Nitro (Mutagenicity)': 'c[N+](=O)[O-]',
        'Epoxide (DNA Alkylation)': 'C1OC1',
        'Aziridine (Mutagenicity)': 'C1NC1',
        'Primary Aromatic Amine (Carcinogenicity)': 'Nc1ccccc1',
        'Alkyl Halide (Alkylating Agent)': '[C][F,Cl,Br,I]',
        'Hydrazine (Hepatotoxicity)': 'NN',
        'Nitroso (Carcinogenicity)': 'N=N=O',
        'Quinone (Cytotoxicity)': 'O=C1C=CC(=O)C=C1',
        'Furan (Hepatotoxicity)': 'o1cccc1',
        'Thiophene (Hepatotoxicity)': 's1cccc1',
        'Michael Acceptor (Protein Binding)': 'C=CC=O',
        'Azo Group (Mutagenicity)': 'N=Nc1ccccc1',
        'Acyl Halide (Reactivity)': 'C(=O)[F,Cl,Br,I]',
        'Isocyanate (Respiratory Toxicity)': 'N=C=O',
        'Alkyl Nitrosamine (Carcinogenicity)': 'N(N=O)C',
        'Beta-Lactone (Reactivity)': 'C1OC(=O)C1'
    }
    
    if Chem is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        matched_alerts = []
        for name, smarts in alerts_db.items():
            pattern = Chem.MolFromSmarts(smarts)
            if pattern and mol.HasSubstructMatch(pattern):
                matched_alerts.append(name)
        
        num_alerts = len(matched_alerts)
        
        if num_alerts == 0:
            risk_level = "Low"
            interpretation = "✅ No major structural alerts detected. Low toxicity risk."
        elif num_alerts == 1:
            risk_level = "Medium"
            interpretation = f"⚠️ 1 toxicity alert found. Review and consider modifications."
        else:
            risk_level = "High"
            interpretation = f"🚨 {num_alerts} toxicity alerts found. High risk - redesign recommended."
        
        return {
            'alerts_found': matched_alerts,
            'num_alerts': num_alerts,
            'risk_level': risk_level,
            'interpretation': interpretation
        }
    except Exception as e:
        logger.error(f"Error checking toxicity alerts: {e}")
        return None


def calculate_comprehensive_properties(smiles):
    """
    Calculate comprehensive drug discovery properties
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: All properties combined
    """
    if Chem is None or Descriptors is None or rdMolDescriptors is None:
        logger.error("RDKit is not available")
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        # Additional properties
        qed = Descriptors.qed(mol) if hasattr(Descriptors, 'qed') else None
        aromatic_rings = Descriptors.NumAromaticRings(mol)
        aliphatic_rings = Descriptors.NumAliphaticRings(mol)
        chiral_centers = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
        sp3_fraction = rdMolDescriptors.CalcFractionCSP3(mol)
        
        return {
            'QED': round(qed, 3) if qed else None,
            'Aromatic_Rings': aromatic_rings,
            'Aliphatic_Rings': aliphatic_rings,
            'Chiral_Centers': chiral_centers,
            'Sp3_Fraction': round(sp3_fraction, 3)
        }
    except Exception as e:
        logger.error(f"Error calculating comprehensive properties: {e}")
        return {}


def get_all_drug_likeness_metrics(smiles):
    """
    Get all drug-likeness metrics for a molecule
    
    Args:
        smiles (str): SMILES string
        
    Returns:
        dict: Complete drug-likeness profile
    """
    if Chem is None:
        logger.error("RDKit is not available for drug-likeness calculations")
        return None
    return {
        'solubility': predict_esol_solubility(smiles),
        'lipinski': check_lipinski_rule_of_five(smiles),
        'veber': check_veber_rule(smiles),
        'ghose': check_ghose_filter(smiles),
        'toxicity': check_toxicity_alerts(smiles),
        'additional_properties': calculate_comprehensive_properties(smiles)
    }
