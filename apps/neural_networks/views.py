"""
Neural network prediction API views
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.molecules.models import Molecule
from apps.admin_dashboard.models import PredictionRequest
from .predictors import (
    toxicity_predictor,
    solubility_predictor,
    drug_likeness_predictor,
    bioactivity_predictor
)
import logging

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def predict_toxicity(request, molecule_id=None):
    """Predict toxicity for a molecule"""
    try:
        if molecule_id:
            molecule = get_object_or_404(Molecule, id=molecule_id)
            smiles = molecule.smiles
        else:
            smiles = request.data.get('smiles') or request.GET.get('smiles')
            if not smiles:
                return Response(
                    {'error': 'SMILES string required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            molecule = None
        
        # Make prediction using Ollama
        result = ollama_predictor.predict_toxicity(smiles)
        
        # Log prediction request
        if request.user.is_authenticated:
            PredictionRequest.objects.create(
                user=request.user,
                molecule=molecule,
                prediction_type='toxicity',
                input_data={'smiles': smiles},
                result=result
            )
        
        # Update molecule if exists
        if molecule and result['toxicity_score'] is not None:
            molecule.toxicity_score = result['toxicity_score']
            molecule.save()
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Toxicity prediction error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def predict_solubility(request, molecule_id=None):
    """Predict solubility for a molecule"""
    try:
        if molecule_id:
            molecule = get_object_or_404(Molecule, id=molecule_id)
            smiles = molecule.smiles
        else:
            smiles = request.data.get('smiles') or request.GET.get('smiles')
            if not smiles:
                return Response(
                    {'error': 'SMILES string required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            molecule = None
        
        # Make prediction using Ollama
        result = ollama_predictor.predict_solubility(smiles)
        
        # Log prediction request
        if request.user.is_authenticated:
            PredictionRequest.objects.create(
                user=request.user,
                molecule=molecule,
                prediction_type='solubility',
                input_data={'smiles': smiles},
                result=result
            )
        
        # Update molecule if exists
        if molecule and result['log_solubility'] is not None:
            molecule.solubility = result['log_solubility']
            molecule.save()
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Solubility prediction error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def predict_drug_likeness(request, molecule_id=None):
    """Predict drug-likeness for a molecule"""
    try:
        if molecule_id:
            molecule = get_object_or_404(Molecule, id=molecule_id)
            smiles = molecule.smiles
        else:
            smiles = request.data.get('smiles') or request.GET.get('smiles')
            if not smiles:
                return Response(
                    {'error': 'SMILES string required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            molecule = None
        
        # Make prediction
        result = drug_likeness_predictor.predict(smiles)
        
        # Log prediction request
        if request.user.is_authenticated:
            PredictionRequest.objects.create(
                user=request.user,
                molecule=molecule,
                prediction_type='drug_likeness',
                input_data={'smiles': smiles},
                result=result
            )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Drug-likeness prediction error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def predict_bioactivity(request, molecule_id=None):
    """Predict bioactivity for a molecule"""
    try:
        if molecule_id:
            molecule = get_object_or_404(Molecule, id=molecule_id)
            smiles = molecule.smiles
            target_gene = molecule.gene_target
        else:
            smiles = request.data.get('smiles') or request.GET.get('smiles')
            target_gene = request.data.get('target_gene') or request.GET.get('target_gene')
            if not smiles:
                return Response(
                    {'error': 'SMILES string required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            molecule = None
        
        # Make prediction
        result = bioactivity_predictor.predict(smiles, target_gene)
        
        # Log prediction request
        if request.user.is_authenticated:
            PredictionRequest.objects.create(
                user=request.user,
                molecule=molecule,
                prediction_type='bioactivity',
                input_data={'smiles': smiles, 'target_gene': target_gene},
                result=result
            )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Bioactivity prediction error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def predict_all(request, molecule_id=None):
    """Run all predictions for a molecule"""
    try:
        if molecule_id:
            molecule = get_object_or_404(Molecule, id=molecule_id)
            smiles = molecule.smiles
            target_gene = molecule.gene_target
        else:
            smiles = request.data.get('smiles') or request.GET.get('smiles')
            target_gene = request.data.get('target_gene') or request.GET.get('target_gene')
            if not smiles:
                return Response(
                    {'error': 'SMILES string required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            molecule = None
        
        # Run all predictions
        results = {
            'smiles': smiles,
            'toxicity': toxicity_predictor.predict(smiles),
            'solubility': solubility_predictor.predict(smiles),
            'drug_likeness': drug_likeness_predictor.predict(smiles),
            'bioactivity': bioactivity_predictor.predict(smiles, target_gene),
        }
        
        # Log prediction request
        if request.user.is_authenticated:
            PredictionRequest.objects.create(
                user=request.user,
                molecule=molecule,
                prediction_type='comprehensive',
                input_data={'smiles': smiles},
                result=results
            )
        
        # Update molecule if exists
        if molecule:
            if results['toxicity']['toxicity_score'] is not None:
                molecule.toxicity_score = results['toxicity']['toxicity_score']
            if results['solubility']['log_solubility'] is not None:
                molecule.solubility = results['solubility']['log_solubility']
            molecule.save()
        
        return Response(results)
        
    except Exception as e:
        logger.error(f"Comprehensive prediction error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
