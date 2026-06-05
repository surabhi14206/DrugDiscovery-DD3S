"""
Molecular calculation utilities for SMILES processing
Standard methods following chemistry best practices
"""
import logging
import requests
import json

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, SaltRemover
except ImportError as e:
    logger.warning(f"RDKit is not available ({e}). Some molecular features will fall back or return None.")
    Chem = None
    Descriptors = None
    SaltRemover = None


def get_molecular_weight(smiles_string, remove_salts=True):
    """
    Calculate average molecular weight from SMILES string.
    
    Args:
        smiles_string (str): SMILES representation of molecule
        remove_salts (bool): If True, removes salts/solvents before calculation
        
    Returns:
        float: Molecular weight in g/mol, or None if invalid
        
    Rules & Exceptions Handled:
    - Implicit hydrogens (e.g., 'C' = CH4)
    - Salts and solvents (separated by dots)
    - Isotopes (e.g., [13C])
    - Aromatic rings
    - Charged species
    """
    if not smiles_string or not isinstance(smiles_string, str):
        return None
    
    try:
        # Step 1: Handle salt/solvent removal (the dot separator rule)
        if remove_salts and '.' in smiles_string:
            # Take the longest fragment (usually the drug, not the salt)
            fragments = smiles_string.split('.')
            smiles_string = max(fragments, key=len)
            logger.debug(f"Removed salt/solvent, using: {smiles_string}")
        
        # Step 2: Convert SMILES to RDKit Molecule object
        # This automatically handles implicit hydrogens
        mol = Chem.MolFromSmiles(smiles_string)
        
        # Step 3: Validate conversion
        if mol is None:
            logger.warning(f"Invalid SMILES string: {smiles_string}")
            return None
        
        # Step 4: Calculate average molecular weight
        # Uses average atomic weights from periodic table
        # Automatically includes implicit hydrogens
        weight = Descriptors.MolWt(mol)
        
        return round(weight, 2)
        
    except Exception as e:
        logger.error(f"Error calculating molecular weight for '{smiles_string}': {e}")
        return None


def get_exact_molecular_weight(smiles_string, remove_salts=True):
    """
    Calculate exact (monoisotopic) molecular weight.
    Use this for Mass Spectrometry applications.
    
    Returns weight based on most abundant isotope of each element.
    """
    if not smiles_string:
        return None
    
    try:
        if remove_salts and '.' in smiles_string:
            fragments = smiles_string.split('.')
            smiles_string = max(fragments, key=len)
        
        mol = Chem.MolFromSmiles(smiles_string)
        if mol is None:
            return None
        
        # Use exact mass for mass spec calculations
        weight = Descriptors.ExactMolWt(mol)
        return round(weight, 4)
        
    except Exception as e:
        logger.error(f"Error calculating exact weight: {e}")
        return None


def get_molecular_formula(smiles_string, remove_salts=True):
    """
    Calculate molecular formula from SMILES.
    
    Returns:
        str: Molecular formula (e.g., 'C7H10N2O4')
    """
    if not smiles_string:
        return None
    
    try:
        if remove_salts and '.' in smiles_string:
            fragments = smiles_string.split('.')
            smiles_string = max(fragments, key=len)
        
        mol = Chem.MolFromSmiles(smiles_string)
        if mol is None:
            return None
        
        # Get molecular formula with proper Hill notation
        # (C first, then H, then alphabetical)
        formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
        return formula
        
    except Exception as e:
        logger.error(f"Error calculating molecular formula: {e}")
        return None


def sanitize_smiles(smiles_string):
    """
    Clean and standardize SMILES string.
    
    Performs:
    - Salt removal
    - Neutralization of charges (optional)
    - Standardization to canonical form
    
    Returns:
        str: Cleaned SMILES string
    """
    if not smiles_string:
        return None
    
    try:
        # Remove salts using RDKit's SaltRemover
        remover = SaltRemover.SaltRemover()
        
        # Parse SMILES
        mol = Chem.MolFromSmiles(smiles_string)
        if mol is None:
            return smiles_string  # Return original if invalid
        
        # Remove salts
        mol_clean = remover.StripMol(mol)
        
        # Convert back to canonical SMILES
        clean_smiles = Chem.MolToSmiles(mol_clean)
        
        return clean_smiles
        
    except Exception as e:
        logger.error(f"Error sanitizing SMILES: {e}")
        return smiles_string  # Return original on error


def validate_smiles(smiles_string):
    """
    Check if SMILES string is valid.
    
    Returns:
        dict: {
            'valid': bool,
            'error': str or None,
            'canonical_smiles': str or None
        }
    """
    if not smiles_string:
        return {
            'valid': False,
            'error': 'Empty SMILES string',
            'canonical_smiles': None
        }
    
    try:
        mol = Chem.MolFromSmiles(smiles_string)
        
        if mol is None:
            return {
                'valid': False,
                'error': 'Invalid SMILES syntax',
                'canonical_smiles': None
            }
        
        canonical = Chem.MolToSmiles(mol)
        
        return {
            'valid': True,
            'error': None,
            'canonical_smiles': canonical
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'canonical_smiles': None
        }


def calculate_separate_formulas(smiles_string):
    """
    Calculate molecular formula for each disconnected component separately.
    
    For disconnected structures (e.g., "C=C=C.C.C"), returns formulas separated by commas.
    Groups identical formulas with multipliers (e.g., "C3H2²⁺, 2×C").
    
    Args:
        smiles_string (str): SMILES string, may contain '.' for disconnected fragments
    
    Returns:
        str: Comma-separated molecular formulas (e.g., "C3H2²⁺, C, C" or "2×CH3⁺, Cl⁻")
    """
    if not smiles_string or smiles_string.strip() == '':
        return "No molecule drawn"
    
    try:
        # Split into individual fragments using '.' separator
        fragments = [frag.strip() for frag in smiles_string.split('.') if frag.strip()]
        
        if not fragments:
            return "Invalid SMILES"
        
        # Calculate formula for each fragment
        formulas = []
        for frag in fragments:
            try:
                mol = Chem.MolFromSmiles(frag, sanitize=False)
                if mol is None:
                    formulas.append("Invalid")
                else:
                    # Calculate molecular formula with charges
                    formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
                    
                    # Format charges nicely (RDKit uses + and - at the end)
                    # Convert C+ to C⁺, C+2 to C²⁺, etc.
                    formula = format_formula_with_charges(formula)
                    formulas.append(formula)
            except Exception as e:
                logger.warning(f"Error calculating formula for fragment '{frag}': {e}")
                formulas.append("Invalid")
        
        # Group identical formulas and add multipliers
        from collections import Counter
        formula_counts = Counter(formulas)
        
        result_parts = []
        for formula, count in formula_counts.items():
            if count > 1:
                result_parts.append(f"{count}×{formula}")
            else:
                result_parts.append(formula)
        
        return ", ".join(result_parts)
        
    except Exception as e:
        logger.error(f"Error in calculate_separate_formulas: {e}")
        return "Error calculating formula"


def format_formula_with_charges(formula):
    """
    Format molecular formula with proper charge notation.
    Converts C+ to C⁺, C+2 to C²⁺, C- to C⁻, C-2 to C²⁻, etc.
    
    Args:
        formula (str): Formula from RDKit (e.g., "C4H2+2" or "Cl-")
    
    Returns:
        str: Formatted formula with superscript charges
    """
    import re
    
    # Superscript digits mapping
    superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', 
                      '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                      '+': '⁺', '-': '⁻'}
    
    # Match charge at end: +, -, +2, -3, etc.
    charge_pattern = r'([+-]\d*)$'
    match = re.search(charge_pattern, formula)
    
    if match:
        charge_str = match.group(1)
        base_formula = formula[:match.start()]
        
        # Convert charge to superscript
        formatted_charge = ''
        for char in charge_str:
            if char in superscript_map:
                formatted_charge += superscript_map[char]
            else:
                formatted_charge += char
        
        # Rearrange: number comes before sign (e.g., ²⁺ not ⁺²)
        # RDKit gives +2, we want ²⁺
        if len(formatted_charge) > 1:
            # Has both sign and number
            sign = formatted_charge[0]  # ⁺ or ⁻
            number = formatted_charge[1:]  # ², ³, etc.
            if number:  # If there's a number
                formatted_charge = number + sign
        
        return base_formula + formatted_charge
    
    return formula


def get_molecular_properties(smiles_string, remove_salts=True):
    """
    Calculate comprehensive molecular properties from SMILES.
    
    Returns:
        dict: {
            'molecular_weight': float,
            'exact_weight': float,
            'molecular_formula': str,  # Now handles disconnected fragments properly
            'num_atoms': int,
            'num_heavy_atoms': int,
            'num_h_donors': int,
            'num_h_acceptors': int,
            'logp': float,
            'tpsa': float (Topological Polar Surface Area),
            'num_rotatable_bonds': int,
            'canonical_smiles': str
        }
    """
    if not smiles_string:
        return None
    
    try:
        # Calculate molecular formula for disconnected components
        molecular_formula = calculate_separate_formulas(smiles_string)
        
        # For other properties, use the largest fragment if remove_salts is True
        working_smiles = smiles_string
        if remove_salts and '.' in smiles_string:
            fragments = smiles_string.split('.')
            working_smiles = max(fragments, key=len)
        
        mol = Chem.MolFromSmiles(working_smiles)
        if mol is None:
            return None
        
        properties = {
            'molecular_weight': round(Descriptors.MolWt(mol), 2),
            'exact_weight': round(Descriptors.ExactMolWt(mol), 4),
            'molecular_formula': molecular_formula,  # Now shows disconnected components
            'num_atoms': mol.GetNumAtoms(),
            'num_heavy_atoms': mol.GetNumHeavyAtoms(),
            'num_h_donors': Descriptors.NumHDonors(mol),
            'num_h_acceptors': Descriptors.NumHAcceptors(mol),
            'logp': round(Descriptors.MolLogP(mol), 2),
            'tpsa': round(Descriptors.TPSA(mol), 2),
            'num_rotatable_bonds': Descriptors.NumRotatableBonds(mol),
            'canonical_smiles': Chem.MolToSmiles(mol)
        }
        
        return properties
        
    except Exception as e:
        logger.error(f"Error calculating molecular properties: {e}")
        return None


def get_pdb_id_from_smiles(smiles_string, match_type='graph-exact', timeout=10):
    """
    Query RCSB PDB to find PDB IDs containing a ligand matching the SMILES.
    
    Args:
        smiles_string (str): SMILES representation of molecule
        match_type (str): 'graph-exact' (exact match) or 'graph-relaxed' (similar structures)
        timeout (int): Request timeout in seconds
        
    Returns:
        str: First PDB ID found (e.g., '1ABC'), or None if not found
        
    Note: A single molecule may appear in multiple PDB entries. This returns
    the first match. For specific protein targets, use get_pdb_ids_by_target().
    """
    if not smiles_string:
        logger.warning("Empty SMILES string provided to PDB search")
        return None
    
    try:
        # Clean SMILES (remove salts) before searching
        clean_smiles = sanitize_smiles(smiles_string)
        if not clean_smiles:
            clean_smiles = smiles_string
        
        # RCSB PDB Search API endpoint
        url = "https://search.rcsb.org/rcsbsearch/v2/query"
        
        # Construct query JSON
        query = {
            "query": {
                "type": "terminal",
                "service": "chemical",
                "parameters": {
                    "value": clean_smiles,
                    "type": "descriptor",
                    "descriptor_type": "SMILES",
                    "match_type": match_type
                }
            },
            "return_type": "entry"
        }
        
        logger.debug(f"Querying PDB for SMILES: {clean_smiles}")
        
        response = requests.post(url, json=query, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got results
            if data.get("result_set") and len(data["result_set"]) > 0:
                pdb_id = data["result_set"][0]["identifier"]
                logger.info(f"Found PDB ID {pdb_id} for SMILES: {clean_smiles}")
                return pdb_id
            else:
                logger.info(f"No PDB entries found for SMILES: {clean_smiles}")
                return None
        else:
            logger.warning(f"PDB API returned status {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"PDB API request timeout after {timeout}s")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"PDB API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching PDB ID: {e}")
        return None


def get_all_pdb_ids_from_smiles(smiles_string, match_type='graph-exact', limit=10):
    """
    Get multiple PDB IDs for a molecule (since one ligand can be in many structures).
    
    Args:
        smiles_string (str): SMILES representation
        match_type (str): 'graph-exact' or 'graph-relaxed'
        limit (int): Maximum number of PDB IDs to return
        
    Returns:
        list: List of PDB IDs (e.g., ['1ABC', '2DEF', '3GHI'])
    """
    if not smiles_string:
        return []
    
    try:
        clean_smiles = sanitize_smiles(smiles_string) or smiles_string
        
        url = "https://search.rcsb.org/rcsbsearch/v2/query"
        
        query = {
            "query": {
                "type": "terminal",
                "service": "chemical",
                "parameters": {
                    "value": clean_smiles,
                    "type": "descriptor",
                    "descriptor_type": "SMILES",
                    "match_type": match_type
                }
            },
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "return_all_hits": False
            }
        }
        
        response = requests.post(url, json=query, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("result_set"):
                pdb_ids = [entry["identifier"] for entry in data["result_set"][:limit]]
                logger.info(f"Found {len(pdb_ids)} PDB IDs for SMILES")
                return pdb_ids
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching multiple PDB IDs: {e}")
        return []


def get_ligand_info_from_pdb(pdb_id):
    """
    Get information about ligands in a specific PDB structure.
    
    Args:
        pdb_id (str): PDB ID (e.g., '1ABC')
        
    Returns:
        dict: {
            'pdb_id': str,
            'ligands': list of dict with ligand info,
            'title': str,
            'resolution': float
        }
    """
    if not pdb_id:
        return None
    
    try:
        # RCSB PDB Data API
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.upper()}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            result = {
                'pdb_id': pdb_id.upper(),
                'title': data.get('struct', {}).get('title', 'N/A'),
                'resolution': None,
                'ligands': []
            }
            
            # Get resolution if available
            if 'rcsb_entry_info' in data:
                result['resolution'] = data['rcsb_entry_info'].get('resolution_combined', [None])[0]
            
            return result
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching PDB info for {pdb_id}: {e}")
        return None


def search_pdb_by_target_and_ligand(target_name, smiles_string):
    """
    Search for PDB entries containing both a specific target protein and ligand.
    
    Args:
        target_name (str): Target protein name (e.g., 'ALDH1A1')
        smiles_string (str): Ligand SMILES
        
    Returns:
        list: PDB IDs matching both criteria
    """
    if not target_name or not smiles_string:
        return []
    
    try:
        clean_smiles = sanitize_smiles(smiles_string) or smiles_string
        
        url = "https://search.rcsb.org/rcsbsearch/v2/query"
        
        # Combined query: chemical + target name
        query = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "chemical",
                        "parameters": {
                            "value": clean_smiles,
                            "type": "descriptor",
                            "descriptor_type": "SMILES",
                            "match_type": "graph-relaxed"
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_phrase",
                            "value": target_name
                        }
                    }
                ]
            },
            "return_type": "entry"
        }
        
        response = requests.post(url, json=query, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("result_set"):
                pdb_ids = [entry["identifier"] for entry in data["result_set"]]
                logger.info(f"Found {len(pdb_ids)} PDB entries for {target_name} + ligand")
                return pdb_ids
        
        return []
        
    except Exception as e:
        logger.error(f"Error searching PDB by target and ligand: {e}")
        return []


# ==============================================================================
# AI-POWERED DRUG SUMMARY GENERATION
# ==============================================================================

def get_drug_data_from_openfda(drug_name):
    """
    Fetch technical drug data from OpenFDA API.
    
    Args:
        drug_name (str): Brand name or generic name of the drug
        
    Returns:
        dict: Dictionary containing raw medical data or error message
    """
    try:
        # Search OpenFDA label endpoint for drug information
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}&limit=1"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            # Try generic name search
            url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{drug_name}&limit=1"
            response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                
                # Extract key medical information
                drug_data = {
                    "indications": result.get("indications_and_usage", ["Not available"])[0],
                    "warnings": result.get("warnings", ["Not available"])[0],
                    "dosage": result.get("dosage_and_administration", ["Not available"])[0],
                    "adverse_reactions": result.get("adverse_reactions", ["Not available"])[0],
                    "description": result.get("description", ["Not available"])[0],
                }
                
                return drug_data
        
        return {"error": f"Could not find FDA data for '{drug_name}'"}
        
    except Exception as e:
        logger.error(f"Error fetching OpenFDA data: {e}")
        return {"error": f"Error fetching data: {str(e)}"}


def get_drug_data_from_pubchem(smiles_string, molecule_name):
    """
    Fetch chemical and drug information from PubChem.
    
    Args:
        smiles_string (str): SMILES representation of the molecule
        molecule_name (str): Name of the molecule
        
    Returns:
        dict: Dictionary containing PubChem data
    """
    try:
        import pubchempy as pcp
        
        # Search by SMILES or name
        compounds = pcp.get_compounds(smiles_string, 'smiles')
        
        if not compounds:
            compounds = pcp.get_compounds(molecule_name, 'name')
        
        if compounds:
            compound = compounds[0]
            
            # Get available properties
            drug_data = {
                "molecular_formula": compound.molecular_formula,
                "molecular_weight": compound.molecular_weight,
                "iupac_name": compound.iupac_name,
                "synonyms": compound.synonyms[:5] if compound.synonyms else [],
                "cid": compound.cid,
            }
            
            return drug_data
        
        return {"error": "Compound not found in PubChem"}
        
    except Exception as e:
        logger.error(f"Error fetching PubChem data: {e}")
        return {"error": f"Error: {str(e)}"}


def generate_layman_summary_with_ai(drug_name, raw_data, molecule_properties=None):
    """
    Generate a layman-friendly drug summary using LOCAL Ollama AI (phi3 model).
    Runs completely offline - no API keys needed!
    
    Args:
        drug_name (str): Name of the drug/compound
        raw_data (dict): Raw medical/chemical data
        molecule_properties (dict): Additional molecular properties (optional)
        
    Returns:
        str: Layman-friendly summary or error message
    """
    try:
        import ollama
        
        # Prepare the context for AI (keep it concise for 4B parameter models)
        context = f"Drug/Compound: {drug_name}\n\n"
        
        # Add molecular properties if available
        if molecule_properties:
            context += "Properties:\n"
            for key, value in molecule_properties.items():
                if value:
                    context += f"- {key}: {value}\n"
            context += "\n"
        
        # Add raw data (truncate heavily for small models)
        if "error" not in raw_data:
            context += "Medical Info:\n"
            for key, value in raw_data.items():
                if value and value != "Not available":
                    # Strict truncation for 4B models (smaller context window)
                    truncated_value = str(value)[:800] + "..." if len(str(value)) > 800 else value
                    context += f"\n{key.upper()}:\n{truncated_value}\n"
        
        # Limit total context to 2000 characters for small models
        context = context[:2000]
        
        # Generate AI summary using local Ollama (gemma3:4b model)
        response = ollama.chat(
            model='gemma3:4b',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a medical assistant. Explain this drug compound in 3-4 simple sentences '
                        'that a patient can understand. No medical jargon. Focus on: what it does, '
                        'how it works, and key safety notes.'
                    )
                },
                {
                    'role': 'user',
                    'content': f"Please explain this drug simply:\n\n{context}"
                }
            ],
            options={
                'temperature': 0.7,
                'num_predict': 300,  # Max tokens for response
            }
        )
        
        summary = response['message']['content']
        
        # Add powered by footer
        powered_by = (
            "\n\n**Powered by**: Gemma3 (4B) - Running locally on your computer (100% free & private)"
        )
        
        return summary + powered_by
        
    except ConnectionError as e:
        logger.error(f"Ollama connection error: {e}")
        return (
            "❌ **Ollama Not Running**\n\n"
            "To use AI summaries, you need to:\n\n"
            "1. Download Ollama from: https://ollama.com/download\n"
            "2. Install and open the Ollama app\n"
            "3. Run in terminal: `ollama pull gemma3:4b`\n"
            "4. Refresh this page and try again\n\n"
            "💡 Ollama is 100% free and runs on your computer (no API keys needed!)"
        )
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check for common errors
        if "not found" in error_msg:
            return (
                "❌ **Model Not Downloaded**\n\n"
                "Please run this command in your terminal:\n"
                "```\n"
                "ollama pull gemma3:4b\n"
                "```\n\n"
                "This downloads the Gemma3 model (~2.5 GB). It's a one-time download."
            )
        elif "connection refused" in error_msg or "connect" in error_msg:
            return (
                "❌ **Ollama Not Running**\n\n"
                "Please open the Ollama app on your computer.\n"
                "Download from: https://ollama.com/download"
            )
        
        logger.error(f"Error generating AI summary: {e}")
        return f"Error generating summary: {str(e)}"


def get_comprehensive_drug_summary(molecule_name, smiles_string=None, gene_target=None):
    """
    Main function to get a comprehensive layman-friendly drug summary.
    Combines data from multiple sources and generates AI summary.
    
    Args:
        molecule_name (str): Name of the molecule/drug
        smiles_string (str): SMILES representation (optional)
        gene_target (str): Gene target information (optional)
        
    Returns:
        dict: Complete drug summary with raw data and AI explanation
    """
    result = {
        "molecule_name": molecule_name,
        "raw_data": {},
        "layman_summary": "",
        "data_sources": []
    }
    
    # Try to fetch from OpenFDA first
    fda_data = get_drug_data_from_openfda(molecule_name)
    if "error" not in fda_data:
        result["raw_data"]["fda"] = fda_data
        result["data_sources"].append("OpenFDA")
    
    # Get PubChem data if SMILES available
    if smiles_string:
        pubchem_data = get_drug_data_from_pubchem(smiles_string, molecule_name)
        if "error" not in pubchem_data:
            result["raw_data"]["pubchem"] = pubchem_data
            result["data_sources"].append("PubChem")
    
    # Prepare molecule properties
    molecule_properties = {}
    if smiles_string:
        molecule_properties["SMILES"] = smiles_string
    if gene_target:
        molecule_properties["Target Gene"] = gene_target
    
    # Generate AI summary
    combined_data = {}
    if "fda" in result["raw_data"]:
        combined_data.update(result["raw_data"]["fda"])
    elif "pubchem" in result["raw_data"]:
        combined_data.update(result["raw_data"]["pubchem"])
    
    result["layman_summary"] = generate_layman_summary_with_ai(
        molecule_name,
        combined_data,
        molecule_properties
    )
    
    return result


def fetch_molecule_from_pdb(pdb_id):
    """
    Fetch molecule structure from PDB database and create a temporary Molecule object
    
    Args:
        pdb_id (str): PDB ID to fetch
        
    Returns:
        Molecule object or None if not found
    """
    from .models import Molecule
    
    try:
        # Try to get from local database first by PDB ID
        if str(pdb_id).upper().startswith('PDB:'):
            pdb_code = str(pdb_id)[4:]
        else:
            pdb_code = str(pdb_id)
            
        # Check if already exists
        existing = Molecule.objects.filter(pdb_id=pdb_code).first()
        if existing:
            return existing
            
        # Fetch from PDB API
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_code}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"PDB entry {pdb_code} not found")
            return None
            
        pdb_data = response.json()
        
        # Get ligand information
        ligand_url = f"https://data.rcsb.org/rest/v1/core/chemcomp/{pdb_code}"
        ligand_response = requests.get(ligand_url, timeout=10)
        
        if ligand_response.status_code == 200:
            ligand_data = ligand_response.json()
            smiles = ligand_data.get('chem_comp', {}).get('pdbx_smiles_canonical', '')
            name = ligand_data.get('chem_comp', {}).get('name', f'PDB_{pdb_code}')
            formula = ligand_data.get('chem_comp', {}).get('formula', '')
        else:
            # Use basic info from entry
            smiles = ''
            name = pdb_data.get('struct', {}).get('title', f'PDB_{pdb_code}')
            formula = ''
        
        # Calculate molecular properties if SMILES available
        mol_weight = None
        if smiles:
            mol_weight = get_molecular_weight(smiles)
            if not formula:
                formula = get_molecular_formula(smiles)
        
        # Create temporary molecule object (not saved to database)
        molecule = Molecule(
            pdb_id=pdb_code,
            name=name,
            smiles=smiles or '',
            molecular_formula=formula or '',
            molecular_weight=mol_weight,
            gene_target='',
            is_active=False
        )
        
        # Save to database for future use
        molecule.save()
        logger.info(f"Fetched and saved molecule from PDB: {pdb_code}")
        
        return molecule
        
    except Exception as e:
        logger.error(f"Error fetching from PDB: {e}")
        return None
