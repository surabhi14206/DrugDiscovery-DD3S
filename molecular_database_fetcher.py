"""
Database Utilities for Fetching Molecular Data
Integrates PubChem, ChEMBL, and ZINC databases for high-quality training data
"""
import requests
import json
import time
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PubChemFetcher:
    """Fetch molecular data from PubChem"""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    @staticmethod
    def fetch_compounds_by_formula(formula, max_results=1000):
        """
        Fetch compounds by molecular formula
        
        Args:
            formula: Molecular formula (e.g., "C6H6" for benzene)
            max_results: Maximum number of results to fetch
            
        Returns:
            List of compound data with SMILES
        """
        try:
            # Search by formula
            url = f"{PubChemFetcher.BASE_URL}/compound/formula/{formula}/cids/JSON"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch formula {formula}: {response.status_code}")
                return []
            
            cids = response.json().get('IdentifierList', {}).get('CID', [])[:max_results]
            
            if not cids:
                return []
            
            # Fetch SMILES for CIDs (batch request)
            compounds = []
            batch_size = 100
            
            for i in range(0, len(cids), batch_size):
                batch = cids[i:i+batch_size]
                cid_str = ','.join(map(str, batch))
                
                prop_url = f"{PubChemFetcher.BASE_URL}/compound/cid/{cid_str}/property/CanonicalSMILES,MolecularFormula/JSON"
                
                try:
                    prop_response = requests.get(prop_url, timeout=30)
                    if prop_response.status_code == 200:
                        data = prop_response.json().get('PropertyTable', {}).get('Properties', [])
                        compounds.extend(data)
                        time.sleep(0.2)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error fetching batch: {e}")
                    continue
            
            logger.info(f"Fetched {len(compounds)} compounds for formula {formula}")
            return compounds
            
        except Exception as e:
            logger.error(f"Error fetching from PubChem: {e}")
            return []
    
    @staticmethod
    def fetch_random_compounds(count=1000):
        """Fetch random compounds from PubChem"""
        compounds = []
        
        # Common molecular formulas
        formulas = [
            "C6H6", "C7H8", "C8H10", "C6H5OH", "C2H5OH",
            "C6H12O6", "C3H8O", "CH4N2O", "C9H8O4",
            "C10H16N2O", "C8H9NO2", "C6H8O7"
        ]
        
        for formula in formulas:
            batch = PubChemFetcher.fetch_compounds_by_formula(formula, max_results=count//len(formulas))
            compounds.extend(batch)
            
            if len(compounds) >= count:
                break
        
        return compounds[:count]


class ChEMBLFetcher:
    """Fetch molecular data from ChEMBL"""
    
    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
    
    @staticmethod
    def fetch_molecules(limit=1000, offset=0):
        """
        Fetch molecules from ChEMBL
        
        Args:
            limit: Number of molecules to fetch
            offset: Starting offset
            
        Returns:
            List of molecule data with SMILES
        """
        try:
            url = f"{ChEMBLFetcher.BASE_URL}/molecule.json"
            params = {
                'limit': min(limit, 1000),
                'offset': offset
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch from ChEMBL: {response.status_code}")
                return []
            
            data = response.json()
            molecules = data.get('molecules', [])
            
            # Extract SMILES
            results = []
            for mol in molecules:
                if 'molecule_structures' in mol and mol['molecule_structures']:
                    smiles = mol['molecule_structures'].get('canonical_smiles')
                    if smiles:
                        results.append({
                            'CID': mol.get('molecule_chembl_id'),
                            'CanonicalSMILES': smiles,
                            'MolecularFormula': mol.get('molecule_properties', {}).get('full_molformula', '')
                        })
            
            logger.info(f"Fetched {len(results)} molecules from ChEMBL")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching from ChEMBL: {e}")
            return []
    
    @staticmethod
    def fetch_drug_molecules(limit=5000):
        """Fetch drug-like molecules from ChEMBL"""
        molecules = []
        batch_size = 1000
        
        for offset in range(0, limit, batch_size):
            batch = ChEMBLFetcher.fetch_molecules(limit=batch_size, offset=offset)
            molecules.extend(batch)
            time.sleep(0.5)  # Rate limiting
            
            if len(molecules) >= limit:
                break
        
        return molecules[:limit]


class MolecularDataset:
    """Unified interface for fetching and managing molecular data"""
    
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def fetch_and_cache(self, source='pubchem', count=10000, force_refresh=False):
        """
        Fetch data from source and cache locally
        
        Args:
            source: 'pubchem', 'chembl', or 'both'
            count: Number of molecules to fetch
            force_refresh: Force re-download even if cached
            
        Returns:
            List of SMILES strings
        """
        cache_file = self.cache_dir / f'{source}_smiles_{count}.json'
        
        # Check cache
        if cache_file.exists() and not force_refresh:
            logger.info(f"Loading from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Fetch data
        logger.info(f"Fetching {count} molecules from {source}...")
        compounds = []
        
        if source == 'pubchem' or source == 'both':
            logger.info("Fetching from PubChem...")
            pubchem_data = PubChemFetcher.fetch_random_compounds(count // 2 if source == 'both' else count)
            compounds.extend(pubchem_data)
        
        if source == 'chembl' or source == 'both':
            logger.info("Fetching from ChEMBL...")
            chembl_data = ChEMBLFetcher.fetch_drug_molecules(count // 2 if source == 'both' else count)
            compounds.extend(chembl_data)
        
        # Extract SMILES
        smiles_list = []
        for comp in compounds:
            smiles = comp.get('CanonicalSMILES')
            if smiles and len(smiles) > 3 and len(smiles) < 200:
                smiles_list.append(smiles)
        
        # Remove duplicates
        smiles_list = list(set(smiles_list))
        
        # Cache
        with open(cache_file, 'w') as f:
            json.dump(smiles_list, f)
        
        logger.info(f"Fetched and cached {len(smiles_list)} unique SMILES")
        return smiles_list
    
    def validate_smiles_with_rdkit(self, smiles_list):
        """Validate SMILES using RDKit"""
        try:
            from rdkit import Chem
            
            valid_smiles = []
            for smiles in smiles_list:
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    # Get canonical SMILES
                    canonical = Chem.MolToSmiles(mol)
                    valid_smiles.append(canonical)
            
            logger.info(f"Validated {len(valid_smiles)}/{len(smiles_list)} SMILES with RDKit")
            return valid_smiles
            
        except ImportError:
            logger.warning("RDKit not available, skipping validation")
            return smiles_list


def fetch_training_data(count=10000, source='both', validate=True):
    """
    Convenience function to fetch high-quality training data
    
    Args:
        count: Number of molecules to fetch
        source: 'pubchem', 'chembl', or 'both'
        validate: Validate with RDKit
        
    Returns:
        List of validated SMILES strings
    """
    dataset = MolecularDataset()
    smiles_list = dataset.fetch_and_cache(source=source, count=count)
    
    if validate:
        smiles_list = dataset.validate_smiles_with_rdkit(smiles_list)
    
    return smiles_list


if __name__ == '__main__':
    # Test fetching
    print("Testing PubChem fetcher...")
    pubchem_data = PubChemFetcher.fetch_random_compounds(count=100)
    print(f"Fetched {len(pubchem_data)} compounds from PubChem")
    
    if pubchem_data:
        print("\nSample SMILES:")
        for comp in pubchem_data[:5]:
            print(f"  {comp.get('CanonicalSMILES')}")
    
    print("\nTesting ChEMBL fetcher...")
    chembl_data = ChEMBLFetcher.fetch_molecules(limit=100)
    print(f"Fetched {len(chembl_data)} molecules from ChEMBL")
    
    if chembl_data:
        print("\nSample SMILES:")
        for comp in chembl_data[:5]:
            print(f"  {comp.get('CanonicalSMILES')}")
