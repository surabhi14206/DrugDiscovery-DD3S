"""
PDB API Integration Service
Handles fetching molecule data from RCSB PDB
"""
import requests
from typing import Dict, List, Optional
from Bio import PDB
import io


class PDBAPIClient:
    """Client for RCSB PDB REST API"""
    
    BASE_URL = "https://data.rcsb.org/rest/v1/core"
    FILES_URL = "https://files.rcsb.org/download"
    SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PDB-Clone/1.0',
            'Accept': 'application/json'
        })
    
    def get_entry(self, pdb_id: str) -> Optional[Dict]:
        """
        Fetch basic entry information for a PDB ID
        
        Args:
            pdb_id: 4-character PDB identifier
            
        Returns:
            Dictionary with entry data or None if not found
        """
        try:
            url = f"{self.BASE_URL}/entry/{pdb_id.upper()}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching PDB entry {pdb_id}: {e}")
            return None
    
    def get_structure_file(self, pdb_id: str, file_format: str = 'pdb') -> Optional[str]:
        """
        Download structure file for a PDB ID
        
        Args:
            pdb_id: 4-character PDB identifier
            file_format: 'pdb', 'cif', or 'xml'
            
        Returns:
            Structure file content as string or None
        """
        try:
            url = f"{self.FILES_URL}/{pdb_id.upper()}.{file_format}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error downloading structure file for {pdb_id}: {e}")
            return None
    
    def search_by_ligand(self, smiles: str) -> List[str]:
        """
        Search for PDB entries containing a ligand with given SMILES
        
        Args:
            smiles: SMILES string of the ligand
            
        Returns:
            List of PDB IDs
        """
        query = {
            "query": {
                "type": "terminal",
                "service": "text_chem",
                "parameters": {
                    "value": smiles,
                    "type": "descriptor",
                    "descriptor_type": "SMILES"
                }
            },
            "return_type": "entry"
        }
        
        try:
            response = self.session.post(self.SEARCH_URL, json=query)
            response.raise_for_status()
            data = response.json()
            
            if 'result_set' in data:
                return [result['identifier'] for result in data['result_set']]
            return []
        except requests.RequestException as e:
            print(f"Error searching by SMILES: {e}")
            return []
    
    def get_ligand_info(self, pdb_id: str, ligand_id: str) -> Optional[Dict]:
        """
        Fetch information about a specific ligand in a PDB entry
        
        Args:
            pdb_id: 4-character PDB identifier
            ligand_id: 3-character ligand identifier
            
        Returns:
            Dictionary with ligand data or None
        """
        try:
            url = f"{self.BASE_URL}/nonpolymer_entity/{pdb_id}/{ligand_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching ligand info for {pdb_id}/{ligand_id}: {e}")
            return None


class StructureParser:
    """Parse PDB/CIF structure files"""
    
    def __init__(self):
        self.parser = PDB.PDBParser(QUIET=True)
        self.cif_parser = PDB.MMCIFParser(QUIET=True)
    
    def parse_pdb_string(self, pdb_string: str) -> Optional[PDB.Structure.Structure]:
        """
        Parse PDB format string into Structure object
        
        Args:
            pdb_string: PDB file content as string
            
        Returns:
            BioPython Structure object or None
        """
        try:
            pdb_io = io.StringIO(pdb_string)
            structure = self.parser.get_structure('structure', pdb_io)
            return structure
        except Exception as e:
            print(f"Error parsing PDB structure: {e}")
            return None
    
    def extract_ligands(self, structure: PDB.Structure.Structure) -> List[Dict]:
        """
        Extract ligand information from structure
        
        Args:
            structure: BioPython Structure object
            
        Returns:
            List of dictionaries with ligand data
        """
        ligands = []
        
        for model in structure:
            for chain in model:
                for residue in chain:
                    # Check if residue is a HETATM (ligand/water/ion)
                    if residue.id[0].startswith('H_'):
                        ligand_name = residue.resname
                        atoms = []
                        
                        for atom in residue:
                            atoms.append({
                                'name': atom.name,
                                'element': atom.element,
                                'coord': atom.coord.tolist()
                            })
                        
                        ligands.append({
                            'name': ligand_name,
                            'chain': chain.id,
                            'residue_num': residue.id[1],
                            'atoms': atoms
                        })
        
        return ligands
    
    def get_structure_info(self, structure: PDB.Structure.Structure) -> Dict:
        """
        Extract basic information from structure
        
        Args:
            structure: BioPython Structure object
            
        Returns:
            Dictionary with structure information
        """
        atom_count = 0
        residue_count = 0
        chain_ids = []
        
        for model in structure:
            for chain in model:
                if chain.id not in chain_ids:
                    chain_ids.append(chain.id)
                    
                for residue in chain:
                    residue_count += 1
                    atom_count += len(residue)
        
        return {
            'num_atoms': atom_count,
            'num_residues': residue_count,
            'num_chains': len(chain_ids),
            'chain_ids': chain_ids
        }


class SMILESProcessor:
    """Process SMILES strings for molecular analysis"""
    
    @staticmethod
    def validate_smiles(smiles: str) -> bool:
        """
        Validate SMILES string format
        
        Args:
            smiles: SMILES string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation - check for common issues
        if not smiles or not isinstance(smiles, str):
            return False
        
        # Check for balanced parentheses
        if smiles.count('(') != smiles.count(')'):
            return False
        
        # Check for balanced brackets
        if smiles.count('[') != smiles.count(']'):
            return False
        
        return True
    
    @staticmethod
    def normalize_smiles(smiles: str) -> str:
        """
        Normalize SMILES string (basic cleanup)
        
        Args:
            smiles: SMILES string to normalize
            
        Returns:
            Normalized SMILES string
        """
        # Remove whitespace
        smiles = smiles.strip()
        
        # Remove any salt/fragment separators (.)
        if '.' in smiles:
            # Take the largest fragment
            fragments = smiles.split('.')
            smiles = max(fragments, key=len)
        
        return smiles
