from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Molecule, MoleculeProperty
from .serializers import MoleculeSerializer
import logging

logger = logging.getLogger(__name__)

from .utils import (
    get_molecular_weight, 
    get_molecular_formula, 
    get_molecular_properties,
    validate_smiles,
    sanitize_smiles,
    get_pdb_id_from_smiles,
    get_all_pdb_ids_from_smiles,
    search_pdb_by_target_and_ligand
)


class MoleculeViewSet(viewsets.ModelViewSet):
    """API endpoint for molecules"""
    queryset = Molecule.objects.all()
    serializer_class = MoleculeSerializer


@api_view(['GET'])
def search_molecules(request):
    """
    Search molecules API
    
    Query Parameters:
    - q: General search (searches name, gene_target, smiles)
    - gene_target: Filter by gene target
    - is_active: Filter by activity status (true/false)
    - name: Filter by name
    - smiles: Filter by SMILES string
    """
    from django.db.models import Q
    
    molecules = Molecule.objects.all()
    
    # General search query
    q = request.GET.get('q', '').strip()
    if q:
        molecules = molecules.filter(
            Q(name__icontains=q) |
            Q(gene_target__icontains=q) |
            Q(smiles__icontains=q) |
            Q(molecular_formula__icontains=q)
        )
    
    # Specific filters
    gene_target = request.GET.get('gene_target', '').strip()
    if gene_target:
        molecules = molecules.filter(gene_target__icontains=gene_target)
    
    name = request.GET.get('name', '').strip()
    if name:
        molecules = molecules.filter(name__icontains=name)
    
    smiles = request.GET.get('smiles', '').strip()
    if smiles:
        molecules = molecules.filter(smiles__icontains=smiles)
    
    is_active = request.GET.get('is_active', '').strip().lower()
    if is_active in ['true', '1', 'yes']:
        molecules = molecules.filter(is_active=True)
    elif is_active in ['false', '0', 'no']:
        molecules = molecules.filter(is_active=False)
    
    # Limit results
    limit = request.GET.get('limit', '50')
    try:
        limit = int(limit)
        limit = min(limit, 1000)  # Max 1000 results
    except ValueError:
        limit = 50
    
    molecules = molecules[:limit]
    
    serializer = MoleculeSerializer(molecules, many=True)
    
    return Response({
        'count': len(serializer.data),
        'results': serializer.data,
        'query': {
            'q': q,
            'gene_target': gene_target,
            'name': name,
            'is_active': is_active,
            'limit': limit
        }
    })


@api_view(['GET'])
def predict_toxicity(request, molecule_id):
    """Predict toxicity for a molecule"""
    try:
        molecule = Molecule.objects.get(id=molecule_id)
        # Prediction logic will be implemented
        result = {
            'toxicity_score': 0.5,
            'risk_level': 'Moderate',
            'message': 'Prediction module will be implemented'
        }
        return Response(result)
    except Molecule.DoesNotExist:
        return Response({'error': 'Molecule not found'}, status=404)


@api_view(['GET'])
def predict_solubility(request, molecule_id):
    """Predict solubility for a molecule"""
    try:
        molecule = Molecule.objects.get(id=molecule_id)
        result = {
            'log_solubility': -3.5,
            'solubility_class': 'Moderately Soluble',
            'message': 'Prediction module will be implemented'
        }
        return Response(result)
    except Molecule.DoesNotExist:
        return Response({'error': 'Molecule not found'}, status=404)


@api_view(['GET'])
def predict_activity(request, molecule_id):
    """Predict biological activity for a molecule"""
    try:
        molecule = Molecule.objects.get(id=molecule_id)
        result = {
            'activity_score': 0.75,
            'confidence': 0.89,
            'message': 'Prediction module will be implemented'
        }
        return Response(result)
    except Molecule.DoesNotExist:
        return Response({'error': 'Molecule not found'}, status=404)


@api_view(['POST'])
def calculate_properties(request):
    """
    Calculate molecular properties from SMILES string.
    
    POST body:
    {
        "smiles": "CC(=O)O",
        "remove_salts": true  (optional, default: true)
    }
    
    Returns comprehensive molecular properties including:
    - Molecular weight (average and exact)
    - Molecular formula
    - Number of atoms, heavy atoms
    - H-bond donors/acceptors
    - LogP, TPSA
    - Number of rotatable bonds
    """
    smiles = request.data.get('smiles', '').strip()
    remove_salts = request.data.get('remove_salts', True)
    
    if not smiles:
        return Response(
            {'error': 'SMILES string is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate SMILES first
    validation = validate_smiles(smiles)
    if not validation['valid']:
        return Response(
            {
                'error': 'Invalid SMILES string',
                'details': validation['error']
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate properties
    properties = get_molecular_properties(smiles, remove_salts=remove_salts)
    
    if properties is None:
        return Response(
            {'error': 'Failed to calculate properties'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'smiles': smiles,
        'canonical_smiles': properties['canonical_smiles'],
        'properties': properties,
        'validation': validation
    })


@api_view(['POST'])
def validate_smiles_api(request):
    """
    Validate a SMILES string and return canonical form.
    
    POST body:
    {
        "smiles": "CC(=O)O"
    }
    """
    smiles = request.data.get('smiles', '').strip()
    
    if not smiles:
        return Response(
            {'error': 'SMILES string is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = validate_smiles(smiles)
    
    if not result['valid']:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@api_view(['POST'])
def sanitize_smiles_api(request):
    """
    Clean and standardize a SMILES string (remove salts, standardize format).
    
    POST body:
    {
        "smiles": "CC(=O)O.Na"
    }
    """
    smiles = request.data.get('smiles', '').strip()
    
    if not smiles:
        return Response(
            {'error': 'SMILES string is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    clean_smiles = sanitize_smiles(smiles)
    
    if clean_smiles is None:
        return Response(
            {'error': 'Failed to sanitize SMILES'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'original_smiles': smiles,
        'sanitized_smiles': clean_smiles,
        'changes_made': smiles != clean_smiles
    })


@api_view(['POST'])
def generate_ml_smiles_api(request):
    """
    Generate SMILES string using ML model (LSTM-based character generation).
    
    POST body (optional):
    {
        "temperature": 0.8,  // 0.5-1.5, controls randomness
        "count": 1           // number of SMILES to generate
    }
    """
    try:
        from .ml_smiles_service import generate_ml_smiles
        
        temperature = float(request.data.get('temperature', 0.8))
        count = int(request.data.get('count', 1))
        
        # Validate parameters
        temperature = max(0.5, min(1.5, temperature))
        count = max(1, min(10, count))
        
        results = []
        for i in range(count):
            result = generate_ml_smiles(temperature=temperature)
            results.append(result)
        
        if count == 1:
            return Response(results[0])
        else:
            return Response({
                'results': results,
                'count': len([r for r in results if r['success']])
            })
            
    except ImportError:
        return Response({
            'error': 'ML model not available. Please train the model first.',
            'success': False
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def lookup_pdb_id(request):
    """
    Look up PDB ID(s) for a molecule from its SMILES string.
    
    POST body:
    {
        "smiles": "CC(=O)O",
        "match_type": "graph-exact",  // optional: "graph-exact" or "graph-relaxed"
        "get_all": false  // optional: return all PDB IDs or just first match
    }
    
    Returns:
    {
        "smiles": "CC(=O)O",
        "pdb_id": "1ABC",  // if get_all=false
        "pdb_ids": ["1ABC", "2DEF"],  // if get_all=true
        "found": true,
        "match_type": "graph-exact"
    }
    """
    smiles = request.data.get('smiles', '').strip()
    match_type = request.data.get('match_type', 'graph-exact')
    get_all = request.data.get('get_all', False)
    
    if not smiles:
        return Response(
            {'error': 'SMILES string is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if match_type not in ['graph-exact', 'graph-relaxed']:
        return Response(
            {'error': 'match_type must be "graph-exact" or "graph-relaxed"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        if get_all:
            pdb_ids = get_all_pdb_ids_from_smiles(smiles, match_type=match_type)
            return Response({
                'smiles': smiles,
                'pdb_ids': pdb_ids,
                'count': len(pdb_ids),
                'found': len(pdb_ids) > 0,
                'match_type': match_type
            })
        else:
            pdb_id = get_pdb_id_from_smiles(smiles, match_type=match_type)
            return Response({
                'smiles': smiles,
                'pdb_id': pdb_id,
                'found': pdb_id is not None,
                'match_type': match_type
            })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to lookup PDB ID: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def search_pdb_by_target(request):
    """
    Search PDB for structures containing both a target protein and a specific ligand.
    
    POST body:
    {
        "target_name": "ALDH1A1",
        "smiles": "CC(=O)O"
    }
    
    Returns:
    {
        "target_name": "ALDH1A1",
        "smiles": "CC(=O)O",
        "pdb_ids": ["1ABC", "2DEF"],
        "count": 2
    }
    """
    target_name = request.data.get('target_name', '').strip()
    smiles = request.data.get('smiles', '').strip()
    
    if not target_name or not smiles:
        return Response(
            {'error': 'Both target_name and smiles are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        pdb_ids = search_pdb_by_target_and_ligand(target_name, smiles)
        
        return Response({
            'target_name': target_name,
            'smiles': smiles,
            'pdb_ids': pdb_ids,
            'count': len(pdb_ids),
            'found': len(pdb_ids) > 0
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to search PDB: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def generate_ai_explanation(request, molecule_id):
    """
    Generate AI-powered layman-friendly explanation for a drug compound.
    
    This uses a two-step process:
    1. Fetch technical data from OpenFDA and PubChem
    2. Generate layman summary using OpenAI API
    """
    try:
        from .utils import get_comprehensive_drug_summary
        
        molecule = Molecule.objects.get(id=molecule_id)
        
        # Get comprehensive drug summary using AI
        summary_data = get_comprehensive_drug_summary(
            molecule_name=molecule.name,
            smiles_string=molecule.smiles,
            gene_target=molecule.gene_target
        )
        
        # Add molecular properties to response
        properties = {
            'molecular_weight': molecule.molecular_weight,
            'molecular_formula': molecule.molecular_formula,
            'toxicity_score': molecule.toxicity_score,
            'solubility': molecule.solubility,
            'is_active': molecule.is_active,
            'gene_target': molecule.gene_target,
            'pdb_id': molecule.pdb_id
        }
        
        return Response({
            'molecule_id': molecule_id,
            'name': molecule.name,
            'explanation': summary_data['layman_summary'],
            'data_sources': summary_data.get('data_sources', []),
            'raw_data': summary_data.get('raw_data', {}),
            'properties': properties
        })
    
    except Molecule.DoesNotExist:
        return Response(
            {'error': f'Molecule with id {molecule_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to generate explanation: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_compound(request):
    """
    Analyze a compound from SMILES string.
    
    POST data:
    - smiles: SMILES string to analyze
    
    Returns:
    - Complete analysis including 2D/3D structures, descriptors, 
      solubility (ESOL), toxicity alerts, and Lipinski compliance
    """
    from .compound_analyzer import CompoundAnalyzer
    import json
    
    logger.info("analyze_compound called")
    
    # Handle both DRF and regular Django requests
    if hasattr(request, 'data'):
        smiles = request.data.get('smiles', '').strip()
    else:
        try:
            data = json.loads(request.body)
            smiles = data.get('smiles', '').strip()
        except:
            smiles = request.POST.get('smiles', '').strip()
    
    logger.info(f"Analyzing SMILES: {smiles}")
    
    if not smiles:
        logger.warning("No SMILES string provided")
        return Response(
            {'error': 'SMILES string is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        analyzer = CompoundAnalyzer()
        logger.info("CompoundAnalyzer initialized")
        results = analyzer.analyze_compound(smiles)
        logger.info(f"Analysis complete. Success: {results.get('success')}")
        
        if not results['success']:
            logger.error(f"Analysis failed: {results.get('error')}")
            return Response(
                {'error': results.get('error', 'Analysis failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Exception in analyze_compound: {e}", exc_info=True)
        return Response(
            {'error': f'Analysis failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def compound_analyzer_view(request):
    """
    Render the compound analyzer page.
    """
    return render(request, 'molecules/compound_analyzer.html')

@api_view(['GET'])
def generate_3d_structure(request):
    """
    Generate 3D structure from SMILES using RDKit.
    
    Query Parameters:
    - smiles: SMILES string
    
    Returns:
    - SDF format text for 3D visualization
    """
    from django.http import HttpResponse
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        Chem = None
        AllChem = None
    
    # Check if RDKit is available
    if Chem is None or AllChem is None:
        return HttpResponse('RDKit is not available. Please ensure RDKit is properly installed and unblocked.', status=500)
    
    smiles = request.GET.get('smiles', '').strip()
    
    if not smiles:
        return HttpResponse('SMILES parameter is required', status=400)
    
    try:
        # Parse SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return HttpResponse('Invalid SMILES string', status=400)
        
        # Add hydrogens
        mol_with_h = Chem.AddHs(mol)
        
        # Generate 3D coordinates using ETKDG
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        params.maxIterations = 1000
        
        result = AllChem.EmbedMolecule(mol_with_h, params)
        
        if result == -1:
            # Fallback to basic embedding
            result = AllChem.EmbedMolecule(mol_with_h, AllChem.ETKDG())
            if result == -1:
                return HttpResponse('Failed to generate 3D coordinates', status=500)
        
        # Optimize with MMFF force field
        props = AllChem.MMFFGetMoleculeProperties(mol_with_h)
        if props is not None:
            ff = AllChem.MMFFGetMoleculeForceField(mol_with_h, props)
            if ff is not None:
                ff.Minimize(maxIts=500)
        
        # Generate MOL block (SDF format)
        mol_block = Chem.MolToMolBlock(mol_with_h)
        
        # Return as plain text SDF
        return HttpResponse(mol_block, content_type='text/plain')
        
    except Exception as e:
        logger.error(f"Error generating 3D structure: {e}", exc_info=True)
        return HttpResponse(f'Failed to generate 3D structure: {str(e)}', status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def name_to_smiles(request):
    """
    Convert molecule name to SMILES and fetch 2D coordinates (for small molecules)
    or fetch PDB structure (for proteins/RNA/DNA)
    """
    import requests
    from django.http import JsonResponse
    
    name = request.data.get('name', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Molecule name is required'}, status=400)
    
    # Protein/RNA/DNA database (matches frontend autocomplete)
    protein_database = {
        'insulin': {'pdb': '1ZNI', 'type': 'protein'},
        'hemoglobin': {'pdb': '1HHO', 'type': 'protein'},
        'lysozyme': {'pdb': '1LYZ', 'type': 'protein'},
        'myoglobin': {'pdb': '1MBO', 'type': 'protein'},
        'collagen': {'pdb': '1CGD', 'type': 'protein'},
        'albumin': {'pdb': '1AO6', 'type': 'protein'},
        'immunoglobulin': {'pdb': '1IGT', 'type': 'protein'},
        'keratin': {'pdb': '3TNU', 'type': 'protein'},
        'rna polymerase': {'pdb': '1I6H', 'type': 'protein'},
        'rna polymerase ii': {'pdb': '1I6H', 'type': 'protein'},
        'rna polymerase iii': {'pdb': '5FJ8', 'type': 'protein'},
        'dna polymerase': {'pdb': '1TAU', 'type': 'protein'},
        'trna': {'pdb': '1EHZ', 'type': 'rna'},
        'transfer rna': {'pdb': '1EHZ', 'type': 'rna'},
        'rrna': {'pdb': '4V9F', 'type': 'rna'},
        'ribosomal rna': {'pdb': '4V9F', 'type': 'rna'},
        'mrna': {'pdb': '1QRS', 'type': 'rna'},
        'messenger rna': {'pdb': '1QRS', 'type': 'rna'},
        'ribosome': {'pdb': '4V9D', 'type': 'complex'},
        'trypsin': {'pdb': '1TLD', 'type': 'protein'},
        'pepsin': {'pdb': '1PSO', 'type': 'protein'},
        'amylase': {'pdb': '1HNY', 'type': 'protein'},
        'lipase': {'pdb': '1LPS', 'type': 'protein'},
        'lactase': {'pdb': '3W37', 'type': 'protein'},
        'catalase': {'pdb': '1DGH', 'type': 'protein'},
        'dna': {'pdb': '1BNA', 'type': 'dna'},
        'dna double helix': {'pdb': '1BNA', 'type': 'dna'},
        'b-dna': {'pdb': '1BNA', 'type': 'dna'},
        'z-dna': {'pdb': '3P4J', 'type': 'dna'},
    }
    
    # Check if this is a known protein/RNA/DNA
    name_lower = name.lower()
    if name_lower in protein_database:
        pdb_info = protein_database[name_lower]
        pdb_id = pdb_info['pdb']
        mol_type = pdb_info['type']
        
        try:
            # Fetch PDB file from RCSB
            pdb_url = f'https://files.rcsb.org/download/{pdb_id}.pdb'
            pdb_response = requests.get(pdb_url, timeout=15)
            
            if pdb_response.status_code == 200:
                return JsonResponse({
                    'success': True,
                    'source': 'PDB',
                    'type': mol_type,
                    'pdb_id': pdb_id,
                    'common_name': name,
                    'pdb_data': pdb_response.text,
                    'is_protein': True
                })
            else:
                return JsonResponse({'error': f'PDB file {pdb_id} not found'}, status=404)
        except Exception as e:
            logger.error(f"PDB fetch error for {pdb_id}: {e}")
            return JsonResponse({'error': f'Failed to fetch PDB structure: {str(e)}'}, status=500)
    
    # For small molecules, use PubChem/CACTUS
    try:
        # Try PubChem first
        try:
            pubchem_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/CanonicalSMILES,MolecularFormula,IUPACName/JSON'
            pubchem_response = requests.get(pubchem_url, timeout=10)
            
            if pubchem_response.status_code == 200:
                data = pubchem_response.json()
                compound = data['PropertyTable']['Properties'][0]
                
                smiles = compound['CanonicalSMILES']
                
                # Get 2D coordinates from NCI CACTUS
                sdf_url = f'https://cactus.nci.nih.gov/chemical/structure/{smiles}/file?format=sdf'
                sdf_response = requests.get(sdf_url, timeout=10)
                
                if sdf_response.status_code == 200:
                    return JsonResponse({
                        'success': True,
                        'source': 'PubChem',
                        'smiles': smiles,
                        'formula': compound.get('MolecularFormula', ''),
                        'iupac_name': compound.get('IUPACName', ''),
                        'common_name': name,
                        'sdf': sdf_response.text,
                        'is_protein': False
                    })
        except Exception as e:
            logger.warning(f"PubChem lookup failed: {e}")
        
        # Try NCI CACTUS as fallback
        try:
            cir_url = f'https://cactus.nci.nih.gov/chemical/structure/{name}/smiles'
            cir_response = requests.get(cir_url, timeout=10)
            
            if cir_response.status_code == 200:
                smiles = cir_response.text.strip()
                
                if smiles and 'html' not in smiles.lower() and 'error' not in smiles.lower():
                    # Get SDF
                    sdf_url = f'https://cactus.nci.nih.gov/chemical/structure/{smiles}/file?format=sdf'
                    sdf_response = requests.get(sdf_url, timeout=10)
                    
                    if sdf_response.status_code == 200:
                        return JsonResponse({
                            'success': True,
                            'source': 'NCI CACTUS',
                            'smiles': smiles,
                            'common_name': name,
                            'sdf': sdf_response.text,
                            'is_protein': False
                        })
        except Exception as e:
            logger.warning(f"NCI CACTUS lookup failed: {e}")
        
        return JsonResponse({'error': 'Molecule not found in any database'}, status=404)
        
    except Exception as e:
        logger.error(f"Name to SMILES conversion error: {e}", exc_info=True)
        return JsonResponse({'error': f'Conversion failed: {str(e)}'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_molecular_structure(request):
    """
    Analyze molecular structure from canvas atoms and bonds.
    Handles disconnected components (multiple molecules) separately.
    Returns proper molecular formulas, SMILES, IUPAC names, and common names.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
    except ImportError:
        Chem = None
        rdMolDescriptors = None
    from django.http import JsonResponse
    from collections import Counter
    import requests
    
    try:
        atoms_data = request.data.get('atoms', [])
        bonds_data = request.data.get('bonds', [])
        
        if not atoms_data:
            return JsonResponse({'error': 'No atoms provided'}, status=400)
        
        # Create RDKit molecule
        em = Chem.EditableMol(Chem.Mol())
        atom_map = {}  # atom_id → RDKit atom index
        
        # Add atoms
        for atom_info in atoms_data:
            atom_id = atom_info.get('id')
            symbol = atom_info.get('element', 'C')
            
            try:
                atom = Chem.Atom(symbol)
                idx = em.AddAtom(atom)
                atom_map[atom_id] = idx
            except Exception as e:
                logger.warning(f"Failed to add atom {symbol}: {e}")
                continue
        
        # Bond type mapping
        bond_type_map = {
            1: Chem.BondType.SINGLE,
            2: Chem.BondType.DOUBLE,
            3: Chem.BondType.TRIPLE,
            1.5: Chem.BondType.AROMATIC,
            '1': Chem.BondType.SINGLE,
            '2': Chem.BondType.DOUBLE,
            '3': Chem.BondType.TRIPLE,
            'single': Chem.BondType.SINGLE,
            'double': Chem.BondType.DOUBLE,
            'triple': Chem.BondType.TRIPLE,
            'aromatic': Chem.BondType.AROMATIC,
        }
        
        # Add bonds
        for bond_info in bonds_data:
            a1 = bond_info.get('from')
            a2 = bond_info.get('to')
            order = bond_info.get('order', 1)
            
            if a1 not in atom_map or a2 not in atom_map:
                continue
            
            if isinstance(order, str):
                order = order.lower()
            
            btype = bond_type_map.get(order, Chem.BondType.SINGLE)
            
            try:
                em.AddBond(atom_map[a1], atom_map[a2], btype)
            except Exception as e:
                logger.warning(f"Failed to add bond {a1}-{a2}: {e}")
                continue
        
        mol = em.GetMol()
        
        # Split into disconnected fragments (separate molecules)
        frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=False)
        
        results = []
        
        for idx, frag in enumerate(frags, 1):
            mol_info = {'component_id': idx}
            error = None
            
            try:
                # Try full sanitization + implicit hydrogens
                Chem.SanitizeMol(frag, sanitizeOps=Chem.SanitizeFlags.SANITIZE_ALL)
                frag_h = Chem.AddHs(frag)
                smiles = Chem.MolToSmiles(frag_h, canonical=True, isomericSmiles=True)
                formula = rdMolDescriptors.CalcMolFormula(frag_h)
                
            except Exception as e:
                # Invalid structure - use explicit atoms only
                error = str(e)
                frag.UpdatePropertyCache(strict=False)
                try:
                    Chem.GetSymmSSSR(frag)  # helps aromatic perception
                except:
                    pass
                smiles = Chem.MolToSmiles(frag, canonical=False, isomericSmiles=False)
                counts = Counter(a.GetSymbol() for a in frag.GetAtoms())
                formula = "".join(
                    f"{el}{cnt}" if cnt > 1 else el 
                    for el, cnt in sorted(counts.items())
                )
                formula += " (explicit atoms only)"
            
            mol_info.update({
                'formula': formula,
                'smiles': smiles,
                'atom_count': frag.GetNumAtoms(),
                'bond_count': frag.GetNumBonds(),
                'has_stereo': any(b.GetStereo() != Chem.BondStereo.STEREONONE for b in frag.GetBonds()),
                'is_aromatic': any(b.GetIsAromatic() for b in frag.GetBonds()),
            })
            
            # Try to get names from PubChem
            if not error and smiles:
                try:
                    # Use PubChem REST API
                    pubchem_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/property/IUPACName,Title/JSON'
                    pubchem_response = requests.get(pubchem_url, timeout=5)
                    
                    if pubchem_response.status_code == 200:
                        data = pubchem_response.json()
                        if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                            props = data['PropertyTable']['Properties'][0]
                            mol_info['iupac_name'] = props.get('IUPACName', 'Unknown')
                            mol_info['common_name'] = props.get('Title', mol_info['iupac_name'])
                        else:
                            mol_info['iupac_name'] = 'Unknown'
                            mol_info['common_name'] = 'Unknown'
                    else:
                        mol_info['iupac_name'] = 'Not found in PubChem'
                        mol_info['common_name'] = 'Unknown'
                        
                except Exception as e:
                    logger.warning(f"PubChem lookup failed: {e}")
                    mol_info['iupac_name'] = 'Name lookup failed'
                    mol_info['common_name'] = 'Name lookup failed'
            else:
                mol_info['iupac_name'] = 'Invalid structure' if error else 'Unknown'
                mol_info['common_name'] = 'Invalid structure' if error else 'Unknown'
            
            if error:
                mol_info['error'] = error
                mol_info['warning'] = 'Structure has valence or bonding issues'
            
            results.append(mol_info)
        
        return JsonResponse({
            'success': True,
            'molecule_count': len(results),
            'molecules': results
        })
        
    except Exception as e:
        logger.error(f"Error analyzing molecular structure: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }, status=500)

