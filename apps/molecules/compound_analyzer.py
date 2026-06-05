"""
Compound Analyzer - Drug Discovery Tools
Calculates molecular properties, toxicity predictions, and solubility from SMILES strings.

Key Concepts:
- SMILES to 2D/3D conversion using RDKit
- ESOL (Estimated Solubility) calculation
- Structural alerts for toxicity (Brenk and PAINS filters)
- Lipinski's Rule of 5 compliance
- Molecular descriptors for drug-likeness
"""

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Crippen, Lipinski
    from rdkit.Chem import rdMolDescriptors
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
except ImportError:
    Chem = None
    AllChem = None
    Descriptors = None
    Crippen = None
    Lipinski = None
    rdMolDescriptors = None
    FilterCatalog = None
    FilterCatalogParams = None
import io
import base64
from typing import Dict, Tuple, Optional
import math
import logging

logger = logging.getLogger(__name__)

# Import drawing module - PIL/Pillow backend should always work
try:
    from rdkit.Chem import Draw
    DRAW_AVAILABLE = True
    logger.info("RDKit Draw module imported successfully")
except (ImportError, OSError) as e:
    logger.error(f"Failed to import RDKit Draw module: {e}")
    DRAW_AVAILABLE = False
    Draw = None


class CompoundAnalyzer:
    """
    Analyzes chemical compounds for drug discovery properties.
    
    Methods:
        parse_smiles: Convert SMILES to RDKit molecule object
        generate_2d_image: Create 2D structure image
        generate_3d_coordinates: Generate 3D conformation
        calculate_descriptors: Compute molecular properties
        calculate_esol_solubility: Estimate aqueous solubility
        check_toxicity_alerts: Screen for toxic substructures
        check_lipinski: Verify Lipinski's Rule of 5
    """
    
    def __init__(self):
        """Initialize filter catalogs for toxicity screening."""
        # Check if RDKit modules are available before initializing catalogs
        if FilterCatalogParams is not None and FilterCatalog is not None:
            # PAINS (Pan Assay INterference compoundS) filter
            params_pains = FilterCatalogParams()
            params_pains.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
            self.pains_catalog = FilterCatalog(params_pains)
            
            # Brenk filter (structural alerts)
            params_brenk = FilterCatalogParams()
            params_brenk.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
            self.brenk_catalog = FilterCatalog(params_brenk)
            logger.info("Filter catalogs initialized successfully")
        else:
            # Set to None if RDKit modules failed to import
            self.pains_catalog = None
            self.brenk_catalog = None
            logger.warning("RDKit FilterCatalog modules not available - toxicity screening will be limited")
    
    def parse_smiles(self, smiles: str) -> Optional[Chem.Mol]:
        """
        Convert SMILES string to RDKit molecule object.
        
        Process:
        1. Parse SMILES text
        2. Sanitize (check chemical validity)
        3. Calculate aromaticity
        
        Args:
            smiles: SMILES string representation
            
        Returns:
            RDKit molecule object or None if invalid
        """
        if Chem is None:
            logger.error("RDKit Chem module not available - cannot parse SMILES")
            return None
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return None
            Chem.SanitizeMol(mol)
            return mol
        except Exception as e:
            print(f"Error parsing SMILES: {e}")
            return None
    
    def generate_2d_image(self, mol: Chem.Mol, size: Tuple[int, int] = (400, 400)) -> str:
        """
        Generate 2D structure image with automatic backend fallback.
        
        Windows Defender may block rdMolDraw2D.dll (false positive).
        This method tries multiple approaches:
        1. Standard Draw.MolToImage() - tries rdMolDraw2D first
        2. Force PIL backend with useCairo=False
        3. Basic Pillow rendering as last resort
        
        Args:
            mol: RDKit molecule object
            size: Image dimensions (width, height)
            
        Returns:
            Base64-encoded PNG image string or None if all methods fail
        """
        if not DRAW_AVAILABLE:
            logger.warning("RDKit Draw module not available - cannot render 2D structures")
            return None
        
        # Compute 2D coordinates first
        try:
            AllChem.Compute2DCoords(mol)
        except Exception as e:
            logger.error(f"Failed to compute 2D coordinates: {e}")
            return None
        
        # Method 1: Try standard rendering (uses rdMolDraw2D if available, falls back automatically)
        try:
            img = Draw.MolToImage(mol, size=size)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            logger.info("2D image generated successfully using default backend")
            return f"data:image/png;base64,{img_base64}"
            
        except (ImportError, OSError) as e:
            # rdMolDraw2D blocked by Windows - try PIL fallback
            logger.warning(f"Standard rendering blocked (likely rdMolDraw2D DLL): {e}")
            
            # Method 2: Force PIL backend explicitly
            try:
                img = Draw.MolToImage(mol, size=size, useCairo=False, kekulize=True)
                
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                
                logger.info("2D image generated using PIL fallback (rdMolDraw2D blocked)")
                return f"data:image/png;base64,{img_base64}"
                
            except Exception as pil_error:
                logger.error(f"PIL fallback also failed: {pil_error}")
                
                # Method 3: Ultra-basic Pillow rendering as last resort
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    
                    # Create blank image with molecule formula as text fallback
                    img = Image.new('RGB', size, color='white')
                    draw = ImageDraw.Draw(img)
                    
                    # Get formula as fallback text
                    from rdkit.Chem import rdMolDescriptors
                    formula = rdMolDescriptors.CalcMolFormula(mol)
                    
                    # Draw formula in center
                    text = f"Formula: {formula}\n(2D rendering blocked)"
                    draw.text((size[0]//4, size[1]//2), text, fill='black')
                    
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                    
                    logger.warning("Using text-only fallback - all drawing backends blocked")
                    return f"data:image/png;base64,{img_base64}"
                    
                except Exception as final_error:
                    logger.error(f"All rendering methods failed: {final_error}", exc_info=True)
                    return None
        
        except Exception as e:
            logger.error(f"Unexpected error in 2D rendering: {e}", exc_info=True)
            return None
    
    def generate_3d_coordinates(self, mol: Chem.Mol) -> Tuple[bool, Optional[str]]:
        """
        Generate 3D molecular conformation.
        
        Process:
        1. Add explicit hydrogens (required for 3D)
        2. Use ETKDG algorithm for initial 3D placement
        3. Apply MMFF94 force field for energy minimization
        4. Export as MOL block for 3D viewers
        
        Args:
            mol: RDKit molecule object
            
        Returns:
            (success: bool, mol_block: str) tuple
        """
        try:
            # Add hydrogens - critical for 3D structure
            mol_with_h = Chem.AddHs(mol)
            
            # ETKDG: Extended distance geometry with knowledge-based constraints
            # Generate multiple conformers and pick the best one
            params = AllChem.ETKDGv3()
            params.randomSeed = 42  # For reproducibility
            params.numThreads = 0  # Use all available threads
            params.useRandomCoords = True
            params.maxIterations = 1000
            
            # Try to embed the molecule
            result = AllChem.EmbedMolecule(mol_with_h, params)
            
            if result == -1:
                # If ETKDG fails, try basic embedding
                result = AllChem.EmbedMolecule(mol_with_h, AllChem.ETKDG())
                if result == -1:
                    return False, "Failed to generate 3D coordinates"
            
            # MMFF94: Merck Molecular Force Field for optimization
            # Use multiple iterations for better convergence
            props = AllChem.MMFFGetMoleculeProperties(mol_with_h)
            if props is not None:
                ff = AllChem.MMFFGetMoleculeForceField(mol_with_h, props)
                if ff is not None:
                    ff.Initialize()
                    ff.Minimize(maxIts=500)  # Increase iterations for better optimization
            else:
                # Fallback to UFF if MMFF fails
                AllChem.UFFOptimizeMolecule(mol_with_h, maxIters=500)
            
            # Convert to MOL block (text format with 3D coordinates)
            mol_block = Chem.MolToMolBlock(mol_with_h)
            
            return True, mol_block
        except Exception as e:
            return False, f"Error generating 3D: {str(e)}"
    
    def calculate_descriptors(self, mol: Chem.Mol) -> Dict:
        """
        Calculate molecular descriptors for drug-likeness.
        
        Descriptors:
        - MW: Molecular Weight (Da)
        - LogP: Lipophilicity (octanol-water partition)
        - TPSA: Topological Polar Surface Area (Ų)
        - HBD: Hydrogen Bond Donors
        - HBA: Hydrogen Bond Acceptors
        - RB: Rotatable Bonds (flexibility)
        - AR: Aromatic Rings
        - AP: Aromatic Proportion
        
        Args:
            mol: RDKit molecule object
            
        Returns:
            Dictionary of descriptor values
        """
        try:
            descriptors = {
                'molecular_formula': rdMolDescriptors.CalcMolFormula(mol) if mol else 'N/A',
                'molecular_weight': round(Descriptors.MolWt(mol), 2) if mol else 0,
                'logp': round(Crippen.MolLogP(mol), 2) if mol else 0,
                'tpsa': round(Descriptors.TPSA(mol), 2) if mol else 0,
                'h_bond_donors': Lipinski.NumHDonors(mol) if mol else 0,
                'h_bond_acceptors': Lipinski.NumHAcceptors(mol) if mol else 0,
                'rotatable_bonds': Lipinski.NumRotatableBonds(mol) if mol else 0,
                'aromatic_rings': rdMolDescriptors.CalcNumAromaticRings(mol) if mol else 0,
                'heavy_atoms': Lipinski.HeavyAtomCount(mol) if mol else 0,
                'formal_charge': Chem.GetFormalCharge(mol) if mol else 0,
                'num_atoms': mol.GetNumAtoms() if mol else 0,
            }
            
            # Aromatic Proportion (used in ESOL)
            if descriptors['heavy_atoms'] > 0:
                num_aromatic_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
                descriptors['aromatic_proportion'] = round(num_aromatic_atoms / descriptors['heavy_atoms'], 3)
            else:
                descriptors['aromatic_proportion'] = 0
            
            return descriptors
        except Exception as e:
            print(f"Error calculating descriptors: {e}")
            import traceback
            traceback.print_exc()
            # Return default values instead of empty dict
            return {
                'molecular_formula': 'N/A',
                'molecular_weight': 0,
                'logp': 0,
                'tpsa': 0,
                'h_bond_donors': 0,
                'h_bond_acceptors': 0,
                'rotatable_bonds': 0,
                'aromatic_rings': 0,
                'heavy_atoms': 0,
                'formal_charge': 0,
                'num_atoms': 0,
                'aromatic_proportion': 0
            }
    
    def calculate_esol_solubility(self, mol: Chem.Mol, descriptors: Dict) -> Dict:
        """
        Calculate aqueous solubility using ESOL (Estimated Solubility) model.
        
        ESOL Formula (Delaney Model):
        LogS = 0.16 - 0.63*LogP - 0.0062*MW + 0.066*RB - 0.74*AP
        
        Where:
        - LogS: Log10 of molar solubility
        - LogP: Lipophilicity
        - MW: Molecular Weight
        - RB: Rotatable Bonds
        - AP: Aromatic Proportion
        
        Advantages over GSE:
        - No melting point required
        - Better for drug-like molecules
        - RMSE ~0.6 log units
        
        Args:
            mol: RDKit molecule object
            descriptors: Pre-calculated descriptors
            
        Returns:
            Dictionary with solubility values and interpretation
        """
        try:
            logp = descriptors.get('logp', 0)
            mw = descriptors.get('molecular_weight', 0)
            rb = descriptors.get('rotatable_bonds', 0)
            ap = descriptors.get('aromatic_proportion', 0)
            
            # ESOL formula
            log_s = 0.16 - (0.63 * logp) - (0.0062 * mw) + (0.066 * rb) - (0.74 * ap)
            
            # Convert to mol/L and mg/mL
            solubility_mol_per_l = 10 ** log_s
            solubility_mg_per_ml = solubility_mol_per_l * mw
            
            # Interpretation classes
            if log_s > -1:
                classification = "Highly Soluble"
            elif log_s > -3:
                classification = "Soluble"
            elif log_s > -5:
                classification = "Moderately Soluble"
            elif log_s > -7:
                classification = "Poorly Soluble"
            else:
                classification = "Insoluble"
            
            return {
                'log_s': round(log_s, 2),
                'solubility_mol_per_l': f"{solubility_mol_per_l:.2e}",
                'solubility_mg_per_ml': round(solubility_mg_per_ml, 4),
                'classification': classification,
                'method': 'ESOL (Delaney)'
            }
        except Exception as e:
            print(f"Error calculating solubility: {e}")
            return {'error': str(e)}
    
    def check_toxicity_alerts(self, mol: Chem.Mol) -> Dict:
        """
        Screen for structural alerts indicating potential toxicity.
        
        Filters Used:
        1. PAINS (Pan Assay INterference compoundS):
           - Compounds that interfere with biological assays
           - False positives in high-throughput screening
           
        2. Brenk Filter:
           - Known toxic or reactive functional groups
           - Mutagenic, carcinogenic, or unstable structures
           
        Substructure Matching Logic:
        - Each filter contains SMARTS patterns
        - Algorithm searches molecule for pattern matches
        - Any match = structural alert flagged
        
        Common Alerts:
        - Nitroso groups (N=O): Mutagenic
        - Epoxides: Reactive, DNA damage
        - Michael acceptors: Covalent protein binding
        - Quinones: Redox cycling, oxidative stress
        
        Args:
            mol: RDKit molecule object
            
        Returns:
            Dictionary with alert flags and matched patterns
        """
        try:
            alerts = {
                'pains_alerts': [],
                'brenk_alerts': [],
                'total_alerts': 0,
                'risk_level': 'Low'
            }
            
            # Check if catalogs are available
            if self.pains_catalog is None or self.brenk_catalog is None:
                alerts['error'] = 'Toxicity screening unavailable - RDKit FilterCatalog modules not loaded'
                logger.warning("Toxicity screening skipped - catalogs not initialized")
                return alerts
            
            # Check PAINS
            if self.pains_catalog.HasMatch(mol):
                matches = self.pains_catalog.GetMatches(mol)
                alerts['pains_alerts'] = [match.GetDescription() for match in matches]
            
            # Check Brenk
            if self.brenk_catalog.HasMatch(mol):
                matches = self.brenk_catalog.GetMatches(mol)
                alerts['brenk_alerts'] = [match.GetDescription() for match in matches]
            
            alerts['total_alerts'] = len(alerts['pains_alerts']) + len(alerts['brenk_alerts'])
            
            # Risk classification
            if alerts['total_alerts'] == 0:
                alerts['risk_level'] = 'Low'
            elif alerts['total_alerts'] <= 2:
                alerts['risk_level'] = 'Moderate'
            else:
                alerts['risk_level'] = 'High'
            
            return alerts
        except Exception as e:
            print(f"Error checking toxicity: {e}")
            return {'error': str(e)}
    
    def check_lipinski(self, descriptors: Dict) -> Dict:
        """
        Check Lipinski's Rule of 5 for drug-likeness.
        
        Lipinski's Rules:
        1. Molecular Weight ≤ 500 Da
        2. LogP ≤ 5 (lipophilicity)
        3. H-Bond Donors ≤ 5
        4. H-Bond Acceptors ≤ 10
        
        Rationale:
        - Oral bioavailability prediction
        - Membrane permeability
        - Absorption in GI tract
        
        Exceptions (still successful drugs):
        - Natural products (e.g., Digoxin)
        - Antibiotics (different absorption mechanisms)
        - CNS drugs (may violate for BBB penetration)
        
        Args:
            descriptors: Pre-calculated molecular descriptors
            
        Returns:
            Dictionary with compliance status and violations
        """
        try:
            mw = descriptors.get('molecular_weight', 0)
            logp = descriptors.get('logp', 0)
            hbd = descriptors.get('h_bond_donors', 0)
            hba = descriptors.get('h_bond_acceptors', 0)
            
            violations = []
            
            if mw > 500:
                violations.append(f"MW > 500 ({mw:.2f} Da)")
            if logp > 5:
                violations.append(f"LogP > 5 ({logp:.2f})")
            if hbd > 5:
                violations.append(f"H-Bond Donors > 5 ({hbd})")
            if hba > 10:
                violations.append(f"H-Bond Acceptors > 10 ({hba})")
            
            compliant = len(violations) == 0
            
            return {
                'compliant': compliant,
                'violations': violations,
                'num_violations': len(violations),
                'interpretation': 'Drug-like (passes Ro5)' if compliant else 'Non-drug-like (Ro5 violations)'
            }
        except Exception as e:
            print(f"Error checking Lipinski: {e}")
            return {'error': str(e)}
    
    def analyze_compound(self, smiles: str) -> Dict:
        """
        Complete compound analysis pipeline.
        
        Workflow:
        1. Parse SMILES → 2D molecule object
        2. Generate 2D image
        3. Generate 3D conformation
        4. Calculate descriptors
        5. Estimate solubility (ESOL)
        6. Screen toxicity alerts
        7. Check Lipinski compliance
        
        Args:
            smiles: SMILES string
            
        Returns:
            Complete analysis results dictionary
        """
        results = {
            'success': False,
            'smiles': smiles,
            'error': None,
            'draw_available': DRAW_AVAILABLE  # Include drawing availability for diagnostics
        }
        
        # Check if RDKit is available
        if Chem is None:
            results['error'] = "RDKit is not available - DLL files may be blocked by Windows. See logs for details."
            logger.error("RDKit Chem module is None - analysis cannot proceed")
            return results
        
        # Log drawing module status
        if DRAW_AVAILABLE:
            logger.info("RDKit Draw module available - will attempt 2D rendering with PIL fallback")
        else:
            logger.warning("RDKit Draw module unavailable - 2D rendering disabled")
        
        try:
            # Step 1: Parse SMILES
            logger.info(f"Parsing SMILES: {smiles}")
            mol = self.parse_smiles(smiles)
            if mol is None:
                results['error'] = "Invalid SMILES string - could not parse"
                logger.error(f"Failed to parse SMILES: {smiles}")
                return results
            
            # Step 2: 2D Image
            logger.info("Generating 2D image")
            try:
                results['image_2d'] = self.generate_2d_image(mol)
                if results['image_2d']:
                    logger.info("2D image generated successfully")
                else:
                    logger.warning("2D image generation returned None - check logs above for specific error")
            except Exception as e:
                logger.error(f"Failed to generate 2D image: {e}")
                results['image_2d'] = None
            
            # Step 3: 3D Coordinates
            logger.info("Generating 3D coordinates")
            try:
                success_3d, mol_block = self.generate_3d_coordinates(mol)
                results['has_3d'] = success_3d
                results['mol_block'] = mol_block if success_3d else None
            except Exception as e:
                logger.error(f"Failed to generate 3D coordinates: {e}")
                results['has_3d'] = False
                results['mol_block'] = None
            
            # Step 4: Descriptors
            logger.info("Calculating descriptors")
            try:
                results['descriptors'] = self.calculate_descriptors(mol)
            except Exception as e:
                logger.error(f"Failed to calculate descriptors: {e}", exc_info=True)
                # Don't return early - continue with other analyses
                results['descriptors'] = None
            
            # Step 5: Solubility
            logger.info("Calculating solubility")
            try:
                if results.get('descriptors'):
                    results['solubility'] = self.calculate_esol_solubility(mol, results['descriptors'])
                else:
                    results['solubility'] = {'error': 'Descriptors not available'}
            except Exception as e:
                logger.error(f"Failed to calculate solubility: {e}")
                results['solubility'] = {'error': str(e)}
            
            # Step 6: Toxicity
            logger.info("Checking toxicity alerts")
            try:
                results['toxicity'] = self.check_toxicity_alerts(mol)
            except Exception as e:
                logger.error(f"Failed to check toxicity: {e}")
                results['toxicity'] = {'error': str(e), 'total_alerts': 0}
            
            # Step 7: Lipinski
            logger.info("Checking Lipinski compliance")
            try:
                if results.get('descriptors'):
                    results['lipinski'] = self.check_lipinski(results['descriptors'])
                else:
                    results['lipinski'] = {'error': 'Descriptors not available', 'compliant': False}
            except Exception as e:
                logger.error(f"Failed to check Lipinski: {e}")
                results['lipinski'] = {'error': str(e), 'compliant': False}
            
            results['success'] = True
            logger.info("Analysis completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Unexpected error in analyze_compound: {e}", exc_info=True)
            results['error'] = f"Analysis failed: {str(e)}"
            return results


# Example usage and testing
if __name__ == "__main__":
    analyzer = CompoundAnalyzer()
    
    # Test with Aspirin
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    results = analyzer.analyze_compound(aspirin_smiles)
    
    print("Aspirin Analysis:")
    print(f"Solubility: {results['solubility']}")
    print(f"Toxicity Alerts: {results['toxicity']['total_alerts']}")
    print(f"Lipinski: {results['lipinski']['compliant']}")
