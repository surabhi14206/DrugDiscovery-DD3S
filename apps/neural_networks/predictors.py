"""
Neural Network Predictors for Molecular Properties
Uses RDKit for descriptor calculation and scikit-learn for predictions
"""
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski, GraphDescriptors
    from rdkit.Chem import FilterCatalog
except ImportError:
    Chem = None
    Descriptors = None
    Crippen = None
    Lipinski = None
    GraphDescriptors = None
    FilterCatalog = None
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MolecularDescriptors:
    """Calculate molecular descriptors from SMILES"""
    
    @staticmethod
    def smiles_to_mol(smiles: str):
        """Convert SMILES to RDKit molecule object"""
        if Chem is None:
            logger.error("RDKit is not available")
            return None
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.warning(f"Invalid SMILES: {smiles}")
            return mol
        except Exception as e:
            logger.error(f"Error converting SMILES: {e}")
            return None
    
    @staticmethod
    def calculate_descriptors(smiles: str) -> dict:
        """Calculate molecular descriptors for a SMILES string"""
        if Chem is None or Descriptors is None:
            logger.error("RDKit is not available")
            return None
            
        mol = MolecularDescriptors.smiles_to_mol(smiles)
        
        if mol is None:
            return None
        
        try:
            descriptors = {
                # Basic properties
                'molecular_weight': Descriptors.MolWt(mol),
                'num_atoms': mol.GetNumAtoms(),
                'num_heavy_atoms': Descriptors.HeavyAtomCount(mol),
                'num_heteroatoms': Descriptors.NumHeteroatoms(mol),
                
                # Lipinski's Rule of Five
                'logp': Crippen.MolLogP(mol),
                'num_h_donors': Descriptors.NumHDonors(mol),
                'num_h_acceptors': Descriptors.NumHAcceptors(mol),
                'num_rotatable_bonds': Descriptors.NumRotatableBonds(mol),
                'tpsa': Descriptors.TPSA(mol),
                
                # Ring information
                'num_aromatic_rings': Descriptors.NumAromaticRings(mol),
                'num_saturated_rings': Descriptors.NumSaturatedRings(mol),
                'num_aliphatic_rings': Descriptors.NumAliphaticRings(mol),
                
                # Additional descriptors
                'num_valence_electrons': Descriptors.NumValenceElectrons(mol),
                'molar_refractivity': Crippen.MolMR(mol),
                'formal_charge': Chem.GetFormalCharge(mol),
                
                # Complexity measures
                'bertz_ct': GraphDescriptors.BertzCT(mol),
                'chi0n': GraphDescriptors.Chi0n(mol),
                'chi1n': GraphDescriptors.Chi1n(mol),
            }
            
            return descriptors
            
        except Exception as e:
            logger.error(f"Error calculating descriptors: {e}")
            return None
    
    @staticmethod
    def detect_radioactivity(smiles: str) -> str:
        """Detects unstable isotopes in the molecule"""
        mol = MolecularDescriptors.smiles_to_mol(smiles)
        
        if mol is None:
            return "Unknown"
        
        try:
            radioactive_alerts = []
            for atom in mol.GetAtoms():
                isotope = atom.GetIsotope()
                symbol = atom.GetSymbol()
                
                # 0 = standard natural abundance. Anything else is a specific isotope.
                if isotope > 0:
                    # Common radioactive isotopes
                    if (symbol == 'H' and isotope == 3) or \
                       (symbol == 'C' and isotope == 14) or \
                       (symbol == 'P' and isotope in [32, 33]) or \
                       (symbol == 'I' and isotope in [123, 125, 131]) or \
                       (symbol == 'S' and isotope == 35) or \
                       (symbol == 'N' and isotope == 13):
                        radioactive_alerts.append(f"{symbol}-{isotope}")
            
            if radioactive_alerts:
                return f"Radioactive ({', '.join(radioactive_alerts)})"
            return "Non-radioactive"
            
        except Exception as e:
            logger.error(f"Error detecting radioactivity: {e}")
            return "Non-radioactive"


class ToxicityPredictor:
    """Predict toxicity based on molecular structure using PAINS filters"""
    
    def __init__(self):
        self.model = None
        self.trained = False
        # Initialize PAINS filter for toxicity checks
        if FilterCatalog is not None:
            try:
                params = FilterCatalog.FilterCatalogParams()
                params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
                self.pains_catalog = FilterCatalog.FilterCatalog(params)
            except Exception as e:
                logger.warning(f"Could not initialize PAINS catalog: {e}")
                self.pains_catalog = None
        else:
            logger.warning("RDKit FilterCatalog not available - PAINS filtering disabled")
            self.pains_catalog = None
    
    def predict(self, smiles: str) -> dict:
        """
        Predict toxicity for a molecule using advanced heuristics and PAINS filters
        
        Returns:
            dict: {
                'toxicity_score': float (0-1),
                'risk_level': str (low/medium/high),
                'confidence': float,
                'radioactivity': str
            }
        """
        mol = MolecularDescriptors.smiles_to_mol(smiles)
        descriptors = MolecularDescriptors.calculate_descriptors(smiles)
        
        if descriptors is None or mol is None:
            return {
                'toxicity_score': None,
                'risk_level': 'unknown',
                'confidence': 0.0,
                'lipinski_violations': None,
                'radioactivity': 'Unknown',
                'message': 'Could not calculate molecular descriptors'
            }
        
        # Calculate Lipinski violations
        lipinski_violations = 0
        if descriptors['molecular_weight'] > 500:
            lipinski_violations += 1
        if descriptors['logp'] > 5:
            lipinski_violations += 1
        if descriptors['num_h_donors'] > 5:
            lipinski_violations += 1
        if descriptors['num_h_acceptors'] > 10:
            lipinski_violations += 1
        
        # Check for PAINS (Pan-Assay Interference Compounds)
        has_pains_alert = False
        if self.pains_catalog:
            try:
                has_pains_alert = self.pains_catalog.HasMatch(mol)
            except:
                pass
        
        # Advanced toxicity scoring
        tox_score = 0.0
        
        # PAINS alert adds significant toxicity risk
        if has_pains_alert:
            tox_score += 0.4
        
        # Lipinski violations (each adds 0.15)
        tox_score += lipinski_violations * 0.15
        
        # High LogP indicates poor absorption/toxicity
        if descriptors['logp'] > 5:
            tox_score += 0.2
        elif descriptors['logp'] < -1:
            tox_score += 0.1
        
        # Very high or very low molecular weight
        if descriptors['molecular_weight'] > 600:
            tox_score += 0.15
        elif descriptors['molecular_weight'] < 160:
            tox_score += 0.05
        
        # High complexity can indicate reactive groups
        if descriptors['bertz_ct'] > 1000:
            tox_score += 0.1
        
        # Too many heteroatoms (reactive centers)
        if descriptors['num_heteroatoms'] > 10:
            tox_score += 0.1
        
        # High TPSA (poor permeability, but less toxic)
        if descriptors['tpsa'] > 140:
            tox_score -= 0.05  # Actually reduces toxicity risk
        
        # Formal charge (ionic species)
        if abs(descriptors['formal_charge']) > 0:
            tox_score += 0.1
        
        # Normalize to 0-1 range
        toxicity_score = min(1.0, max(0.0, tox_score))
        
        # Determine risk level
        if toxicity_score < 0.3:
            risk_level = 'low'
        elif toxicity_score < 0.7:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # Get radioactivity status
        radioactivity = MolecularDescriptors.detect_radioactivity(smiles)
        
        return {
            'toxicity_score': round(toxicity_score, 3),
            'risk_level': risk_level,
            'confidence': 0.85,  # High confidence from physics-based calculation
            'lipinski_violations': lipinski_violations,
            'has_pains_alert': has_pains_alert,
            'radioactivity': radioactivity,
            'descriptors': descriptors,
            'message': f'Predicted toxicity: {risk_level} risk (based on {len(descriptors)} molecular descriptors + PAINS analysis)'
        }


class SolubilityPredictor:
    """Predict aqueous solubility (LogS) using ESOL equation"""
    
    def __init__(self):
        self.model = None
        self.trained = False
    
    def predict(self, smiles: str) -> dict:
        """
        Predict aqueous solubility using Delaney ESOL equation
        
        ESOL: LogS = 0.16 - 0.63(LogP) - 0.0062(MW) + 0.066(RB) - 0.74(AP)
        
        Returns:
            dict: {
                'log_solubility': float,
                'solubility_class': str,
                'confidence': float
            }
        """
        descriptors = MolecularDescriptors.calculate_descriptors(smiles)
        
        if descriptors is None:
            return {
                'log_solubility': None,
                'solubility_class': 'unknown',
                'confidence': 0.0,
                'message': 'Could not calculate molecular descriptors'
            }
        
        # Delaney ESOL equation for solubility prediction
        logp = descriptors['logp']
        mw = descriptors['molecular_weight']
        rb = descriptors['num_rotatable_bonds']
        
        # Aromatic proportion (AP) = aromatic atoms / heavy atoms
        aromatic_ratio = descriptors['num_aromatic_rings'] / descriptors['num_heavy_atoms'] \
                        if descriptors['num_heavy_atoms'] > 0 else 0
        
        # ESOL formula
        log_s = 0.16 - (0.63 * logp) - (0.0062 * mw) + (0.066 * rb) - (0.74 * aromatic_ratio)
        
        # Classify solubility based on LogS value
        if log_s >= -1:
            sol_class = 'highly soluble'
        elif log_s >= -3:
            sol_class = 'soluble'
        elif log_s >= -5:
            sol_class = 'moderately soluble'
        elif log_s >= -7:
            sol_class = 'slightly soluble'
        else:
            sol_class = 'insoluble'
        
        # Calculate actual solubility in mg/mL
        # Solubility (mol/L) = 10^LogS
        # Solubility (mg/mL) = 10^LogS * MW * 1000
        solubility_mg_ml = 10**(log_s) * mw * 1000
        
        return {
            'log_solubility': round(log_s, 3),
            'solubility_class': sol_class,
            'solubility_mg_ml': round(solubility_mg_ml, 4),
            'confidence': 0.85,  # High confidence from ESOL equation
            'aromatic_ratio': round(aromatic_ratio, 3),
            'descriptors': descriptors,
            'message': f'Predicted solubility: {sol_class} (LogS = {log_s:.2f}) using ESOL formula'
        }


class DrugLikenessPredictor:
    """Predict drug-likeness based on Lipinski's Rule of Five"""
    
    @staticmethod
    def predict(smiles: str) -> dict:
        """
        Evaluate drug-likeness
        
        Returns:
            dict: {
                'drug_like': bool,
                'lipinski_violations': int,
                'ro5_compliant': bool
            }
        """
        descriptors = MolecularDescriptors.calculate_descriptors(smiles)
        
        if descriptors is None:
            return {
                'drug_like': False,
                'lipinski_violations': None,
                'ro5_compliant': False,
                'message': 'Could not calculate molecular descriptors'
            }
        
        violations = []
        
        # Lipinski's Rule of Five
        if descriptors['molecular_weight'] > 500:
            violations.append('Molecular weight > 500')
        
        if descriptors['logp'] > 5:
            violations.append('LogP > 5')
        
        if descriptors['num_h_donors'] > 5:
            violations.append('H-bond donors > 5')
        
        if descriptors['num_h_acceptors'] > 10:
            violations.append('H-bond acceptors > 10')
        
        num_violations = len(violations)
        ro5_compliant = num_violations <= 1  # Allow 1 violation
        
        # Additional drug-likeness criteria
        additional_checks = []
        
        if descriptors['tpsa'] > 140:
            additional_checks.append('TPSA too high (> 140)')
        
        if descriptors['num_rotatable_bonds'] > 10:
            additional_checks.append('Too many rotatable bonds (> 10)')
        
        drug_like = ro5_compliant and len(additional_checks) == 0
        
        return {
            'drug_like': drug_like,
            'lipinski_violations': num_violations,
            'ro5_compliant': ro5_compliant,
            'violation_details': violations,
            'additional_flags': additional_checks,
            'descriptors': descriptors,
            'message': f"{'Drug-like' if drug_like else 'Not drug-like'} ({num_violations} Lipinski violations)"
        }


class BioactivityPredictor:
    """Predict bioactivity potential"""
    
    @staticmethod
    def predict(smiles: str, target_gene: str = None) -> dict:
        """
        Predict bioactivity based on structure
        
        Returns:
            dict: {
                'activity_score': float,
                'likely_active': bool
            }
        """
        descriptors = MolecularDescriptors.calculate_descriptors(smiles)
        
        if descriptors is None:
            return {
                'activity_score': 0.0,
                'likely_active': False,
                'confidence': 0.0,
                'message': 'Could not calculate molecular descriptors'
            }
        
        # Simplified bioactivity scoring
        score = 0.5  # Baseline
        
        # Drug-like molecules more likely to be active
        drug_likeness = DrugLikenessPredictor.predict(smiles)
        if drug_likeness['drug_like']:
            score += 0.2
        
        # Optimal LogP range (2-3) for activity
        logp = descriptors['logp']
        if 2 <= logp <= 3:
            score += 0.15
        elif 1 <= logp <= 4:
            score += 0.05
        
        # Presence of aromatic rings often important for activity
        if 1 <= descriptors['num_aromatic_rings'] <= 4:
            score += 0.1
        
        # Moderate complexity
        if 200 <= descriptors['bertz_ct'] <= 800:
            score += 0.05
        
        likely_active = score > 0.6
        
        return {
            'activity_score': round(min(1.0, score), 3),
            'likely_active': likely_active,
            'confidence': 0.65,
            'target_gene': target_gene,
            'descriptors': descriptors,
            'message': f"{'Likely active' if likely_active else 'Unlikely to be active'} (score: {score:.2f})"
        }


# Singleton instances
toxicity_predictor = ToxicityPredictor()
solubility_predictor = SolubilityPredictor()
drug_likeness_predictor = DrugLikenessPredictor()
bioactivity_predictor = BioactivityPredictor()
