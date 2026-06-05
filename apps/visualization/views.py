from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, F, Count, Max
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.molecules.models import Molecule, ImportStatistics
from apps.authentication.models import MoleculeViewHistory
import requests
import markdown
import bleach
import json
from django.conf import settings
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, Crippen, rdMolDescriptors
except ImportError:
    Chem = None
    Descriptors = None
    Lipinski = None
    Crippen = None
    rdMolDescriptors = None
import bleach
import logging
from bs4 import BeautifulSoup
import re
import time

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def get_ai_insights(request):
    """Generate AI insights based on database statistics"""
    try:
        data = json.loads(request.body)
        stats = data.get('stats', {})
        
        # Generate insight based on stats
        total = stats.get('total', 0)
        active = stats.get('active', 0)
        inactive = stats.get('inactive', 0)
        
        if total > 0:
            active_percent = (active / total * 100) if total > 0 else 0
            
            if active_percent > 60:
                insight = f"The database shows a strong bias towards active compounds ({active_percent:.1f}%), which is excellent for training predictive models. This high activity rate suggests well-curated screening data."
            elif active_percent > 40:
                insight = f"The database has a balanced distribution of active ({active_percent:.1f}%) and inactive compounds, ideal for machine learning applications and QSAR modeling."
            else:
                insight = f"The database contains predominantly inactive compounds ({100-active_percent:.1f}% inactive). This is typical of large-scale screening campaigns and provides valuable negative data for model training."
        else:
            insight = "Start by importing molecular data to unlock AI-powered insights and predictive modeling capabilities."
        
        return JsonResponse({
            'success': True,
            'insight': insight,
            'source': 'Statistical Analysis Engine'
        })
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to generate insights'
        }, status=500)


def home(request):
    """Home page with featured molecules and statistics"""
    from django.db.models import Count, Q
    
    # Real-time statistics
    total_molecules = Molecule.objects.count()
    
    # Gene target distribution
    gene_stats = Molecule.objects.values('gene_target').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Activity distribution
    active_count = Molecule.objects.filter(is_active=True).count()
    inactive_count = Molecule.objects.filter(is_active=False).count()
    
    # Get latest import statistics
    latest_import = ImportStatistics.objects.first()  # Gets most recent due to ordering
    
    # Get all molecules for featured section (14,197+ molecules across 7 gene targets)
    featured_molecules = Molecule.objects.all().order_by('-created_at')
    
    context = {
        'total_molecules': total_molecules,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'gene_stats': gene_stats,
        'latest_import': latest_import,
        'featured_molecules': featured_molecules,
    }
    return render(request, 'visualization/home.html', context)


def search(request):
    """Search molecules page"""
    query = request.GET.get('q', '').strip()
    gene_target = request.GET.get('gene_target', '').strip()
    is_active = request.GET.get('is_active', '').strip()
    
    results = Molecule.objects.all()
    
    # Apply search query
    if query:
        results = results.filter(
            Q(name__icontains=query) |
            Q(pdb_id__icontains=query) |
            Q(smiles__icontains=query) |
            Q(molecular_formula__icontains=query) |
            Q(gene_target__icontains=query)
        )
    
    # Apply gene target filter
    if gene_target:
        results = results.filter(gene_target__icontains=gene_target)
    
    # Apply activity filter
    if is_active == 'true':
        results = results.filter(is_active=True)
    elif is_active == 'false':
        results = results.filter(is_active=False)
    
    # Limit results
    results = results[:100]
    
    context = {
        'query': query,
        'results': results,
        'total_results': results.count(),
        'google_cse_id': settings.GOOGLE_CSE_ID,
    }
    return render(request, 'visualization/search.html', context)


def molecule_detail(request, pk):
    """Detail view for a single molecule with 3D visualization and AI chat"""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        Chem = None
        AllChem = None
    
    molecule = get_object_or_404(Molecule, pk=pk)
    
    # Generate 3D coordinates using ETKDGv3 + MMFF94 (same as analyzer)
    mol_block = None
    has_3d = False
    
    if molecule.smiles and Chem is not None and AllChem is not None:
        try:
            mol = Chem.MolFromSmiles(molecule.smiles)
            if mol:
                # Add hydrogens
                mol_with_h = Chem.AddHs(mol)
                
                # ETKDGv3 for 3D coordinate generation
                params = AllChem.ETKDGv3()
                params.randomSeed = 42
                params.numThreads = 0
                params.useRandomCoords = True
                params.maxIterations = 1000
                
                result = AllChem.EmbedMolecule(mol_with_h, params)
                
                if result == -1:
                    # Fallback to basic ETKDG
                    result = AllChem.EmbedMolecule(mol_with_h, AllChem.ETKDG())
                
                if result != -1:
                    # MMFF94 force field optimization
                    props = AllChem.MMFFGetMoleculeProperties(mol_with_h)
                    if props is not None:
                        ff = AllChem.MMFFGetMoleculeForceField(mol_with_h, props)
                        if ff is not None:
                            ff.Initialize()
                            ff.Minimize(maxIts=500)
                    else:
                        # Fallback to UFF
                        AllChem.UFFOptimizeMolecule(mol_with_h, maxIters=500)
                    
                    # Generate MOL block
                    mol_block = Chem.MolToMolBlock(mol_with_h)
                    has_3d = True
        except Exception as e:
            print(f"Error generating 3D coordinates: {e}")
    
    # Track molecule view for authenticated users
    if request.user.is_authenticated:
        history, created = MoleculeViewHistory.objects.get_or_create(
            user=request.user,
            molecule=molecule,
            defaults={'view_count': 1}
        )
        
        if not created:
            # Increment view count and update timestamp
            history.view_count = F('view_count') + 1
            history.save(update_fields=['view_count', 'viewed_at'])
            # Refresh to get the updated count
            history.refresh_from_db()
    
    context = {
        'molecule': molecule,
        'mol_block': mol_block,
        'has_3d': has_3d,
    }
    return render(request, 'visualization/molecule_detail.html', context)


@login_required
@require_http_methods(["POST"])
def get_pdb_from_smiles(request):
    """Use Ollama (local AI) to get PDB ID from SMILES"""
    try:
        data = json.loads(request.body)
        smiles = data.get('smiles', '')
        
        if not smiles:
            return JsonResponse({'error': 'SMILES is required'}, status=400)
        
        # Create prompt for Ollama
        prompt = f"""SMILES: {smiles}

Please provide the PDB ID for this compound. Only respond with the PDB ID if found, or state "No PDB ID found" if not available. Be brief and precise."""
        
        # Call Ollama API (local)
        response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': 'gemma3:4b',
                'messages': [
                    {'role': 'system', 'content': 'You are a cheminformatics expert. Provide PDB IDs for given SMILES notations.'},
                    {'role': 'user', 'content': prompt}
                ],
                'stream': False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            pdb_result = result.get('message', {}).get('content', 'No PDB ID found').strip()
            
            return JsonResponse({
                'success': True,
                'pdb_id': pdb_result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to get response from AI model'
            }, status=500)
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': 'Ollama AI service is not available. Please ensure Ollama is running with gemma3:4b model.'
        }, status=503)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def chat_with_ai(request):
    """Chat with Gemma3:4b about drug discovery and cheminformatics with comprehensive analysis"""
    from apps.molecules.drug_likeness import get_all_drug_likeness_metrics
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        molecule_context = data.get('molecule_context', {})
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Create context-aware system prompt
        system_prompt = """You are a specialized AI assistant focused ONLY on drug discovery and cheminformatics. 
You can ONLY answer questions about:
- Chemical properties and structures (MW, LogP, TPSA, rotatable bonds, etc.)
- Drug discovery processes and ADME properties
- Molecular interactions and mechanisms
- Toxicity and solubility analysis (ESOL, structural alerts)
- Pharmaceutical chemistry and drug-likeness rules (Lipinski, Veber, Ghose)
- Cheminformatics concepts and QSAR
- Bioavailability, permeability, and formulation
- Structural alerts for mutagenicity, carcinogenicity, hepatotoxicity

If asked about anything else (politics, general knowledge, coding, etc.), politely respond that you only discuss drug discovery and cheminformatics topics.

Format your responses with proper Markdown:
- Use **bold** for emphasis
- Use bullet points for lists
- Use ## for section headers
- Organize information into clear sections

Provide detailed, scientif, and structured responses."""
        
        # Build comprehensive context if molecule data is provided
        if molecule_context and molecule_context.get('smiles'):
            smiles = molecule_context['smiles']
            
            # Calculate all drug-likeness metrics
            try:
                metrics = get_all_drug_likeness_metrics(smiles)
                
                context_str = f"\n\n## Current Molecule Analysis\n\n"
                
                # Basic info
                if molecule_context.get('name'):
                    context_str += f"**Name:** {molecule_context['name']}\n"
                if molecule_context.get('smiles'):
                    context_str += f"**SMILES:** {molecule_context['smiles']}\n"
                if molecule_context.get('molecular_formula'):
                    context_str += f"**Formula:** {molecule_context['molecular_formula']}\n"
                if molecule_context.get('molecular_weight'):
                    context_str += f"**Molecular Weight:** {molecule_context['molecular_weight']}\n"
                
                # Add drug-likeness metrics
                if metrics:
                    context_str += "\n### Drug-Likeness Profile\n\n"
                    
                    # Solubility
                    if metrics.get('solubility'):
                        sol = metrics['solubility']
                        context_str += f"**Solubility (ESOL):** logS = {sol['logS']} ({sol['solubility_class']})\n"
                        context_str += f"- {sol['interpretation']}\n\n"
                    
                    # Lipinski
                    if metrics.get('lipinski'):
                        lip = metrics['lipinski']
                        context_str += f"**Lipinski's Rule of Five:** {lip['interpretation']}\n"
                        if lip['violation_details']:
                            context_str += f"- Violations: {', '.join(lip['violation_details'])}\n"
                        context_str += f"- MW: {lip['details']['MW']}, cLogP: {lip['details']['cLogP']}, HBD: {lip['details']['H_Bond_Donors']}, HBA: {lip['details']['H_Bond_Acceptors']}\n\n"
                    
                    # Veber
                    if metrics.get('veber'):
                        veb = metrics['veber']
                        context_str += f"**Veber's Rule:** {veb['interpretation']}\n"
                        context_str += f"- Rotatable Bonds: {veb['details']['Rotatable_Bonds']}, TPSA: {veb['details']['TPSA']} Ų\n\n"
                    
                    # Ghose
                    if metrics.get('ghose'):
                        gho = metrics['ghose']
                        context_str += f"**Ghose Filter:** {gho['interpretation']}\n\n"
                    
                    # Toxicity
                    if metrics.get('toxicity'):
                        tox = metrics['toxicity']
                        context_str += f"**Toxicity Alerts:** {tox['interpretation']}\n"
                        if tox['alerts_found']:
                            context_str += f"- Found: {', '.join(tox['alerts_found'])}\n"
                        context_str += f"- Risk Level: {tox['risk_level']}\n\n"
                    
                    # Additional properties
                    if metrics.get('additional_properties'):
                        props = metrics['additional_properties']
                        context_str += "### Additional Properties\n"
                        if props.get('QED'):
                            context_str += f"- **QED (Drug-likeness Score):** {props['QED']} (0-1 scale, higher is better)\n"
                        if props.get('Aromatic_Rings') is not None:
                            context_str += f"- **Aromatic Rings:** {props['Aromatic_Rings']}\n"
                        if props.get('Chiral_Centers') is not None:
                            context_str += f"- **Chiral Centers:** {props['Chiral_Centers']}\n"
                        if props.get('Sp3_Fraction') is not None:
                            context_str += f"- **Sp3 Fraction:** {props['Sp3_Fraction']} (higher = less flat/aromatic)\n"
                
                system_prompt += context_str
                
            except Exception as e:
                logger.error(f"Error calculating metrics for AI context: {e}")
                # Still include basic context
                context_str = f"\n\nCurrent molecule context:\n"
                if molecule_context.get('name'):
                    context_str += f"Name: {molecule_context['name']}\n"
                if molecule_context.get('smiles'):
                    context_str += f"SMILES: {molecule_context['smiles']}\n"
                system_prompt += context_str
        
        # Call Ollama API with Gemma3:4b (preferred for richer responses)
        ollama_response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': 'gemma3:4b',  # Use Gemma3:4b for molecule-level chat
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': message}
                ],
                'stream': False
            },
            timeout=30
        )
        
        if ollama_response.status_code == 200:
            result = ollama_response.json()
            ai_message = result.get('message', {}).get('content', 'No response generated')
            
            # Convert Markdown to HTML
            html_content = markdown.markdown(
                ai_message,
                extensions=['extra', 'fenced_code', 'tables', 'nl2br']
            )
            
            # Sanitize HTML to prevent XSS attacks (allow safe tags)
            safe_html = bleach.clean(
                html_content,
                tags=['p', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'br', 'code', 'pre', 
                      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'table', 
                      'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'],
                attributes={'a': ['href', 'title'], 'code': ['class'], 'span': ['class']},
                strip=True
            )
            
            return JsonResponse({
                'success': True,
                'response': safe_html
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to get response from AI model'
            }, status=500)
            
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': 'AI service is not available. Please ensure Ollama is running.'
        }, status=503)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def calculate_properties(request):
    """Calculate drug discovery properties from SMILES"""
    # Check authentication for API endpoint
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    # Check if RDKit is available
    if Chem is None or Descriptors is None:
        return JsonResponse({
            'success': False,
            'error': 'RDKit is not available. Please ensure RDKit is properly installed and unblocked.'
        }, status=500)
    
    try:
        data = json.loads(request.body)
        smiles = data.get('smiles', '').strip()
        
        if not smiles:
            return JsonResponse({
                'success': False,
                'error': 'SMILES string is required'
            }, status=400)
        
        # Parse SMILES with RDKit
        mol = Chem.MolFromSmiles(smiles)
        
        if mol is None:
            return JsonResponse({
                'success': False,
                'error': 'Invalid SMILES string'
            }, status=400)
        
        # Calculate molecular descriptors
        properties = {
            'molecular_weight': round(Descriptors.MolWt(mol), 2),
            'logP': round(Crippen.MolLogP(mol), 2),
            'tpsa': round(rdMolDescriptors.CalcTPSA(mol), 2),
            'h_bond_donors': Lipinski.NumHDonors(mol),
            'h_bond_acceptors': Lipinski.NumHAcceptors(mol),
            'rotatable_bonds': Lipinski.NumRotatableBonds(mol),
            'aromatic_rings': Lipinski.NumAromaticRings(mol),
        }
        
        # Lipinski's Rule of Five
        lipinski_violations = 0
        if properties['molecular_weight'] > 500:
            lipinski_violations += 1
        if properties['logP'] > 5:
            lipinski_violations += 1
        if properties['h_bond_donors'] > 5:
            lipinski_violations += 1
        if properties['h_bond_acceptors'] > 10:
            lipinski_violations += 1
        
        properties['lipinski_violations'] = lipinski_violations
        properties['drug_likeness'] = lipinski_violations == 0
        
        return JsonResponse({
            'success': True,
            'properties': properties
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def design(request):
    """Design page for molecule designer tool"""
    context = {
        'title': 'Molecule Designer',
    }
    return render(request, 'visualization/design.html', context)


@require_http_methods(["GET"])
def get_database_stats(request):
    """Get real-time database statistics"""
    from django.db.models import Count, Avg, Max, Min
    
    try:
        # Overall statistics
        total_molecules = Molecule.objects.count()
        active_count = Molecule.objects.filter(is_active=True).count()
        inactive_count = Molecule.objects.filter(is_active=False).count()
        
        # Gene target distribution
        gene_stats = list(Molecule.objects.values('gene_target').annotate(
            count=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False))
        ).order_by('-count'))
        
        # Recent activity
        recent_additions = Molecule.objects.filter(
            created_at__isnull=False
        ).order_by('-created_at')[:5].values('name', 'gene_target', 'created_at')
        
        # Property statistics
        property_stats = Molecule.objects.aggregate(
            avg_weight=Avg('molecular_weight'),
            max_weight=Max('molecular_weight'),
            min_weight=Min('molecular_weight')
        )
        
        # Latest import info
        latest_import = ImportStatistics.objects.first()
        import_info = None
        if latest_import:
            import_info = {
                'source': latest_import.source_file,
                'date': latest_import.import_date.isoformat(),
                'total': latest_import.total_entries,
                'created': latest_import.created_count,
                'updated': latest_import.updated_count,
                'errors': latest_import.error_count
            }
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'total': total_molecules,
                'active': active_count,
                'inactive': inactive_count,
                'gene_distribution': gene_stats,
                'recent_additions': list(recent_additions),
                'property_stats': property_stats,
                'latest_import': import_info
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def get_ai_insights(request):
    """Get AI-powered insights about database statistics using Ollama gemma3:4b"""
    try:
        data = json.loads(request.body)
        stats = data.get('stats', {})
        
        total = stats.get('total', 0)
        active = stats.get('active', 0)
        inactive = stats.get('inactive', 0)
        gene_dist = stats.get('gene_distribution', [])
        active_pct = (active / max(total, 1)) * 100
        
        # Prepare enriched context for AI with more detailed analysis
        context_prompt = f"""
You are a pharmaceutical research analyst. Analyze this drug discovery database and provide detailed, actionable insights:

📊 DATABASE OVERVIEW:
• Total Molecules: {total:,}
• Active Compounds: {active:,} ({active_pct:.1f}%)
• Inactive Compounds: {inactive:,} ({100-active_pct:.1f}%)
• Gene Targets: {len(gene_dist)}

🎯 GENE TARGET DISTRIBUTION:
{chr(10).join([f"• {g.get('gene_target', 'Unknown').upper()}: {g.get('count', 0):,} molecules ({g.get('active', 0)} active, {g.get('inactive', 0)} inactive)" for g in gene_dist[:5]])}

Provide a comprehensive analysis (4-6 sentences) covering:

1. **Data Quality & Balance**: Evaluate the active/inactive ratio and its implications for machine learning model training. Discuss class imbalance and recommend any data augmentation strategies if needed.

2. **Target Diversity**: Analyze the gene target distribution. Identify which targets have the most compounds and discuss the strategic value of this distribution for multi-target drug discovery campaigns.

3. **Drug Discovery Potential**: Assess the dataset's strengths for hit-to-lead optimization, structure-activity relationship (SAR) studies, and predictive modeling. Mention specific applications like QSAR, virtual screening, or lead optimization.

4. **Actionable Recommendations**: Suggest next steps such as:
   - Expanding underrepresented gene targets
   - Running molecular similarity analyses on active clusters
   - Prioritizing targets with high active compound ratios
   - Cross-target polypharmacology exploration

Make it technical but accessible. Use specific percentages and numbers from the data.
"""
        
        try:
            # Try using Ollama gemma3:4b for local AI insights
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'gemma3:4b',
                    'prompt': context_prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'num_predict': 400  # Allow longer, more detailed responses
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                insight = result.get('response', '').strip()
                
                # Convert Markdown to HTML
                html_insight = markdown.markdown(
                    insight,
                    extensions=['extra', 'fenced_code', 'tables', 'nl2br']
                )
                
                # Sanitize HTML
                safe_insight = bleach.clean(
                    html_insight,
                    tags=['p', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'br', 'code', 'pre', 
                          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'table', 
                          'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'],
                    attributes={'a': ['href', 'title'], 'code': ['class'], 'span': ['class']},
                    strip=True
                )
                
                return JsonResponse({
                    'success': True,
                    'insight': safe_insight,
                    'source': 'gemma3:4b AI Engine'
                })
        except Exception as ollama_error:
            # Enhanced fallback with detailed rule-based insights
            insights = []
            
            # 1. Data Balance Analysis
            if active_pct < 10:
                insights.append(f"⚠️ **Highly Imbalanced Dataset**: With only {active_pct:.1f}% active compounds, this dataset exhibits severe class imbalance typical of high-throughput screening campaigns. While the {inactive:,} inactive compounds provide valuable negative examples, consider implementing SMOTE (Synthetic Minority Over-sampling) or cost-sensitive learning to improve model performance on the minority active class.")
            elif active_pct < 30:
                insights.append(f"📊 **Low Activity Rate**: The dataset shows {active_pct:.1f}% active compounds ({active:,} active vs {inactive:,} inactive). This is characteristic of early-stage screening and provides robust negative data for training selectivity into predictive models. The imbalance can be addressed through ensemble methods or by curating additional active hits from related chemical series.")
            elif 30 <= active_pct <= 70:
                insights.append(f"✅ **Well-Balanced Dataset**: With {active_pct:.1f}% active compounds, your database achieves excellent class balance—ideal for training robust machine learning models without extensive resampling. This {active:,} active vs {inactive:,} inactive distribution enables accurate prediction of both hits and non-binders.")
            else:
                insights.append(f"🎯 **High Hit Rate**: An impressive {active_pct:.1f}% activity rate ({active:,} active compounds) indicates highly enriched screening data or focused compound libraries. This is exceptional for lead optimization and SAR studies, though adding more inactive compounds could improve model specificity and reduce false positive rates.")
            
            # 2. Target Diversity Analysis
            if len(gene_dist) > 0:
                top_target = gene_dist[0]
                target_name = top_target.get('gene_target', 'Unknown').upper()
                target_count = top_target.get('count', 0)
                target_pct = (target_count / max(total, 1)) * 100
                target_active = top_target.get('active', 0)
                target_active_pct = (target_active / max(target_count, 1)) * 100
                
                insights.append(f"🎯 **Target Distribution**: Your collection spans {len(gene_dist)} gene targets with {target_name} as the dominant target ({target_count:,} compounds, {target_pct:.1f}% of database, {target_active_pct:.1f}% active). This multi-target coverage enables polypharmacology studies and provides opportunities for identifying dual or multi-target inhibitors—a valuable approach for complex diseases requiring synergistic mechanisms.")
                
                # Identify high-value targets
                high_activity_targets = [g for g in gene_dist if (g.get('active', 0) / max(g.get('count', 1), 1)) > 0.5]
                if high_activity_targets:
                    insights.append(f"💡 **High-Value Targets Identified**: {len(high_activity_targets)} gene target(s) show >50% hit rates, indicating well-validated targets or highly optimized chemical series. Prioritize these for lead optimization and consider chemical space expansion around active scaffolds using similarity searching and bioisosteric replacement strategies.")
            
            # 3. Drug Discovery Applications
            insights.append(f"🔬 **Recommended Applications**: This {total:,}-compound dataset is well-suited for: (1) Training classification models for virtual screening campaigns, (2) Developing QSAR models to predict activity against each target, (3) Scaffold hopping and molecular similarity analyses to identify novel chemotypes, (4) Multi-target QSAR for polypharmacology prediction, and (5) Chemical space visualization using t-SNE or UMAP to identify underexplored regions.")
            
            # 4. Actionable Next Steps
            next_steps = []
            if active_pct < 20:
                next_steps.append("enrich active compound libraries through focused screening")
            if len(gene_dist) < 5:
                next_steps.append("expand target coverage to enable broader therapeutic applications")
            
            underrepresented = [g for g in gene_dist if g.get('count', 0) < (total / len(gene_dist)) * 0.5]
            if underrepresented and len(underrepresented) > 0:
                next_steps.append(f"augment underrepresented targets ({', '.join([g.get('gene_target', 'Unknown').upper() for g in underrepresented[:3]])})")
            
            next_steps.append("perform molecular descriptor analysis to identify key physicochemical drivers of activity")
            next_steps.append("conduct cross-target similarity analysis to discover repurposing opportunities")
            
            insights.append(f"🚀 **Next Steps**: To maximize the value of this dataset, consider: {'; '.join(next_steps)}. Additionally, run fragment-based analysis on your most active clusters to identify privileged substructures for future library design.")
            
            insight = " ".join(insights)
            
            # Convert Markdown to HTML
            html_insight = markdown.markdown(
                insight,
                extensions=['extra', 'fenced_code', 'tables', 'nl2br']
            )
            
            # Sanitize HTML
            safe_insight = bleach.clean(
                html_insight,
                tags=['p', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'br', 'code', 'pre', 
                      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'table', 
                      'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'],
                attributes={'a': ['href', 'title'], 'code': ['class'], 'span': ['class']},
                strip=True
            )
            
            return JsonResponse({
                'success': True,
                'insight': safe_insight,
                'source': 'Advanced Statistical Analysis Engine'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)



@require_http_methods(["GET"])
def web_search_proxy(request):
    """
    Proxy view to search research papers using open/free academic APIs.
    Searches only academic and research paper sources.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)

    openalex_api_key = getattr(settings, 'OPENALEX_API_KEY', '')
    openalex_mailto = getattr(settings, 'OPENALEX_MAILTO', '')
    core_api_key = getattr(settings, 'CORE_API_KEY', '')

    def dedupe_results(results):
        seen = set()
        filtered = []
        for r in results:
            key = r.get('link') or r.get('doi') or r.get('title')
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            filtered.append(r)
        return filtered

    def fetch_openalex(q, limit=10):
        url = "https://api.openalex.org/works"
        params = {
            'search': q,
            'per-page': limit,
            'sort': 'cited_by_count:desc'
        }
        if openalex_mailto:
            params['mailto'] = openalex_mailto

        headers = {}
        if openalex_api_key:
            headers['X-API-Key'] = openalex_api_key

        results = []
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 429:
                logger.error("OpenAlex rate limit reached")
                return results
            if resp.status_code != 200:
                logger.error(f"OpenAlex error: {resp.status_code} - {resp.text[:200]}")
                return results

            data = resp.json()
            for item in data.get('results', []):
                authorships = item.get('authorships') or []
                author_names = []
                for auth in authorships[:3]:
                    author_obj = auth.get('author') or {}
                    name = author_obj.get('display_name')
                    if name:
                        author_names.append(name)
                authors = ", ".join(author_names) if author_names else 'N/A'

                abstract_index = item.get('abstract_inverted_index') or {}
                abstract_tokens = []
                for token, positions in abstract_index.items():
                    for pos in positions:
                        abstract_tokens.append((pos, token))
                abstract_tokens.sort(key=lambda t: t[0])
                abstract_text = " ".join(tok for _, tok in abstract_tokens)
                snippet = abstract_text[:200] if abstract_text else 'No description available.'

                primary_location = item.get('primary_location') or {}
                link = primary_location.get('landing_page_url') or item.get('id', '')
                source_name = primary_location.get('source', {}).get('display_name') or 'OpenAlex'
                doi_val = (item.get('doi') or '').replace('https://doi.org/', '')
                pub_date = item.get('publication_date') or str(item.get('publication_year') or 'N/A')
                is_oa = bool(
                    primary_location.get('is_oa') or
                    (item.get('open_access') or {}).get('is_oa')
                )

                results.append({
                    "title": item.get('display_name', 'Untitled'),
                    "link": link,
                    "snippet": snippet,
                    "source": source_name,
                    "date": pub_date,
                    "authors": authors,
                    "doi": doi_val,
                    "open_access": is_oa
                })
        except Exception as e:
            logger.error(f"OpenAlex fetch failed: {e}")
        return results

    def fetch_core(q, limit=10):
        url = "https://api.core.ac.uk/v3/search/works"
        params = {
            'q': q,
            'page': 1,
            'pageSize': limit
        }
        headers = {'User-Agent': 'DD3S/academic-search'}
        if core_api_key:
            headers['Authorization'] = f"Bearer {core_api_key}"

        results = []
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 429:
                logger.error("CORE API rate limit reached")
                return results
            if resp.status_code != 200:
                logger.error(f"CORE error: {resp.status_code} - {resp.text[:200]}")
                return results

            data = resp.json()
            for item in data.get('results', []):
                title = item.get('title', 'Untitled')
                authors = item.get('authors') or []
                author_names = []
                for auth in authors[:3]:
                    name = auth.get('name') if isinstance(auth, dict) else auth
                    if name:
                        author_names.append(str(name))
                authors_str = ", ".join(author_names) if author_names else 'N/A'

                abstract = item.get('abstract') or 'No description available.'

                link = ''
                full_text = item.get('fullTextLinks') or []
                if full_text and isinstance(full_text, list):
                    link = full_text[0].get('url', '') if isinstance(full_text[0], dict) else ''
                if not link:
                    link = item.get('downloadUrl') or ''
                if not link:
                    doi_val = item.get('doi')
                    if doi_val:
                        link = f"https://doi.org/{doi_val}"

                doi_val = item.get('doi') or ''
                pub_year = item.get('year') or item.get('publishedYear') or 'N/A'
                is_oa = True if full_text else False

                results.append({
                    "title": title,
                    "link": link,
                    "snippet": abstract[:200],
                    "source": "CORE",
                    "date": pub_year,
                    "authors": authors_str,
                    "doi": doi_val,
                    "open_access": is_oa
                })
        except Exception as e:
            logger.error(f"CORE fetch failed: {e}")
        return results

    def fetch_crossref_results(q, limit=8):
        import re

        url = "https://api.crossref.org/works"
        params = {
            'query': q,
            'rows': limit
        }

        results = []
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Crossref error: {resp.status_code} - {resp.text[:200]}")
                return results

            data = resp.json()
            items = data.get('message', {}).get('items', [])

            for item in items:
                title_list = item.get('title') or []
                title = title_list[0] if title_list else 'Untitled'

                # Authors
                authors = item.get('author') or []
                if authors:
                    author_names = [
                        f"{a.get('given', '').strip()} {a.get('family', '').strip()}".strip()
                        for a in authors[:3]
                        if a.get('family') or a.get('given')
                    ]
                    authors_str = ", ".join(filter(None, author_names))
                else:
                    authors_str = 'N/A'

                # Date
                created = item.get('created', {}).get('date-parts', [])
                pub_date = 'N/A'
                if created and created[0]:
                    parts = created[0]
                    pub_date = "-".join(str(p) for p in parts)

                # Snippet
                abstract = item.get('abstract') or ''
                if abstract:
                    snippet = re.sub('<[^<]+?>', '', abstract)
                    snippet = snippet[:200]
                else:
                    container = item.get('container-title') or []
                    snippet = container[0] if container else 'No description available.'

                results.append({
                    "title": title,
                    "link": item.get('URL', ''),
                    "snippet": snippet,
                    "source": "Crossref",
                    "date": pub_date,
                    "authors": authors_str,
                    "doi": (item.get('DOI') or '').strip(),
                    "open_access": False
                })

        except Exception as e:
            logger.error(f"Crossref fallback failed: {e}")
        return results

    def fetch_europe_pmc(q, limit=8):
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            'query': q,
            'pageSize': limit,
            'format': 'json'
        }
        results = []
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Europe PMC error: {resp.status_code} - {resp.text[:200]}")
                return results
            data = resp.json()
            hit_list = data.get('resultList', {}).get('result', [])
            for item in hit_list:
                title = item.get('title', 'Untitled')
                authors = item.get('authorString', 'N/A')
                pub_date = item.get('firstPublicationDate') or item.get('pubYear') or 'N/A'
                abstract = item.get('abstractText') or 'No description available.'
                doi = item.get('doi')
                link = item.get('fullTextUrlList', {}).get('fullTextUrl', [])
                url_val = ''
                if link:
                    url_val = link[0].get('url', '')
                if not url_val:
                    url_val = item.get('id', '')
                results.append({
                    "title": title,
                    "link": url_val,
                    "snippet": abstract[:200],
                    "source": "Europe PMC",
                    "date": pub_date,
                    "authors": authors,
                    "doi": doi,
                    "open_access": True if str(item.get('isOpenAccess', '')).lower() in ['y', 'true', '1'] else False
                })
        except Exception as e:
            logger.error(f"Europe PMC fallback failed: {e}")
        return results

    def fetch_arxiv(q, limit=6):
        import xml.etree.ElementTree as ET
        url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f"all:{q}",
            'start': 0,
            'max_results': limit
        }
        results = []
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"arXiv error: {resp.status_code} - {resp.text[:200]}")
                return results
            root = ET.fromstring(resp.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = (entry.find('atom:title', ns).text or '').strip()
                summary = (entry.find('atom:summary', ns).text or '').strip()
                link_el = entry.find('atom:link[@type="text/html"]', ns)
                link = link_el.get('href') if link_el is not None else ''
                authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns) if a.find('atom:name', ns) is not None]
                published = entry.find('atom:published', ns)
                pub_date = published.text[:10] if published is not None else 'N/A'
                results.append({
                    "title": title or 'Untitled',
                    "link": link,
                    "snippet": summary[:200] if summary else 'No description available.',
                    "source": "arXiv",
                    "date": pub_date,
                    "authors": ", ".join(authors[:3]) if authors else 'N/A',
                    "open_access": True
                })
        except Exception as e:
            logger.error(f"arXiv fallback failed: {e}")
        return results
    
    allowed_domains = [
        'ieeexplore.ieee.org', 'ieee.org', 'ncbi.nlm.nih.gov', 'pubmed', 'nih.gov',
        'europepmc', 'pmc.', '/pmc/articles/', 'biorxiv', 'medrxiv', 'arxiv.org',
        'nature.com', 'science.org', 'sciencemag.org', 'springer', 'wiley', 'acs.org',
        'sciencedirect', 'cell.com', 'jstor.org', 'doi.org', 'openalex', 'core.ac.uk'
    ]
    allowed_keywords = [
        'bio', 'biology', 'biological', 'biochemistry', 'chemistry', 'chemical',
        'cheminformatics', 'chemoinformatics', 'computational chemistry',
        'drug discovery', 'medicinal chemistry', 'pharmacology', 'molecular'
    ]

    def is_relevant(result):
        link = (result.get('link') or '').lower()
        text = f"{result.get('title', '')} {result.get('snippet', '')} {result.get('source', '')}".lower()
        if any(dom in link for dom in allowed_domains):
            return True
        if any(kw in text for kw in allowed_keywords):
            return True
        return False

    aggregated_results = []
    primary_provider = 'openalex'
    used_google = False
    
    try:
        aggregated_results.extend(fetch_openalex(query))
        if len(aggregated_results) < 10:
            aggregated_results.extend(fetch_crossref_results(query))
        if len(aggregated_results) < 10:
            aggregated_results.extend(fetch_europe_pmc(query))
        if len(aggregated_results) < 10:
            aggregated_results.extend(fetch_arxiv(query))
        if len(aggregated_results) < 10:
            aggregated_results.extend(fetch_core(query))

        aggregated_results = dedupe_results(aggregated_results)
        aggregated_results = [r for r in aggregated_results if is_relevant(r)]

    except requests.exceptions.Timeout:
        logger.error("Search request timeout")
        return JsonResponse({
            'error': 'Search request timed out. Please try again.',
            'results': [],
            'count': 0
        }, status=504)

    except Exception as e:
        logger.error(f"Search pipeline failed: {e}")
        aggregated_results = dedupe_results(
            (fetch_crossref_results(query) or []) +
            (fetch_europe_pmc(query) or []) +
            (fetch_arxiv(query) or []) +
            (fetch_openalex(query) or []) +
            (fetch_core(query) or [])
        )

    return JsonResponse({
        'success': True if aggregated_results else False,
        'primary_provider': primary_provider,
        'used_google': used_google,
        'results': aggregated_results,
        'count': len(aggregated_results)
    })



@login_required
def user_dashboard(request):
    """Personal dashboard showing molecule viewing history"""
    # Get user's molecule viewing history
    view_history = MoleculeViewHistory.objects.filter(
        user=request.user
    ).select_related('molecule').order_by('-viewed_at')[:50]  # Last 50 views
    
    # Get statistics
    total_views = view_history.aggregate(total=Count('id'))['total'] or 0
    unique_molecules = MoleculeViewHistory.objects.filter(
        user=request.user
    ).values('molecule').distinct().count()
    
    # Get most viewed molecules
    most_viewed = MoleculeViewHistory.objects.filter(
        user=request.user
    ).values(
        'molecule__id',
        'molecule__name',
        'molecule__pdb_id',
        'molecule__smiles'
    ).annotate(
        total_views=Count('id'),
        last_viewed=Max('viewed_at')
    ).order_by('-total_views')[:10]
    
    context = {
        'view_history': view_history,
        'total_views': total_views,
        'unique_molecules': unique_molecules,
        'most_viewed': most_viewed,
    }
    
    return render(request, 'authentication/dashboard.html', context)


def about(request):
    """About page"""
    return render(request, 'visualization/about.html')


def contact(request):
    """Contact page with full contact details"""
    if request.method == 'POST':
        from apps.admin_dashboard.models import SupportTicket
        from django.contrib import messages
        
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', 'general')
        message = request.POST.get('message', '').strip()
        
        if name and email and message:
            ticket = SupportTicket.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                phone=phone if phone else None,
                subject=subject,
                message=message,
                status='pending',
                priority='medium'
            )
            messages.success(request, 'Your message has been sent successfully! We\'ll respond within 24 hours.')
            return redirect('visualization:contact')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    return render(request, 'visualization/contact.html')


@require_http_methods(["POST"])
def get_drug_likeness_metrics(request):
    """
    Calculate comprehensive drug-likeness metrics for a molecule
    Returns Lipinski, Veber, Ghose, ESOL solubility, and toxicity alerts
    """
    from apps.molecules.drug_likeness import get_all_drug_likeness_metrics
    
    try:
        data = json.loads(request.body)
        smiles = data.get('smiles', '')
        
        if not smiles:
            return JsonResponse({'error': 'SMILES string required'}, status=400)
        
        # Calculate all metrics
        metrics = get_all_drug_likeness_metrics(smiles)
        
        if metrics is None:
            return JsonResponse({'error': 'Invalid SMILES string'}, status=400)
        
        return JsonResponse({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Error calculating drug-likeness metrics: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def summary_view(request):
    """Display a summary/detail page for a search result."""
    url = request.GET.get('url', '')
    title = request.GET.get('title', 'Untitled')
    snippet = request.GET.get('snippet', '')
    q = request.GET.get('q', '')

    return render(request, 'visualization/search_summary.html', {
        'url': url,
        'title': title,
        'snippet': snippet,
        'q': q,
    })
      


@require_http_methods(["POST"])
def summarize_research_paper(request):
    """Fetch and summarize a research paper from its URL"""
    try:
        data = json.loads(request.body)
        url = data.get('url', '')
        title = data.get('title', '')
        snippet = data.get('snippet', '')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        full_text = ''

        def extract_doi(text: str) -> str:
            doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.IGNORECASE)
            return doi_match.group(0) if doi_match else ''

        def fetch_pubmed_by_doi(doi: str):
            """Try PubMed via DOI search; return (title, abstract)."""
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                esearch_url = (
                    'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
                    f'?db=pubmed&retmode=json&term={requests.utils.quote(doi)}[DOI]'
                )
                esearch_resp = requests.get(esearch_url, headers=headers, timeout=15)
                esearch_resp.raise_for_status()
                ids = esearch_resp.json().get('esearchresult', {}).get('idlist', [])
                if not ids:
                    return None, None
                pmid = ids[0]
                eutils_url = (
                    'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
                    f'?db=pubmed&id={pmid}&retmode=xml'
                )
                eutils_response = requests.get(eutils_url, headers=headers, timeout=15)
                eutils_response.raise_for_status()
                xml_soup = BeautifulSoup(eutils_response.text, 'lxml-xml')
                article_title_node = xml_soup.find('ArticleTitle')
                abstract_nodes = xml_soup.find_all('AbstractText')
                article_title_text = (
                    article_title_node.get_text(' ', strip=True)
                    if article_title_node else ''
                )
                abstract_text = ' '.join(
                    node.get_text(' ', strip=True) for node in abstract_nodes
                )
                if not abstract_text and not article_title_text:
                    return None, None
                return article_title_text or None, abstract_text or None
            except requests.RequestException:
                return None, None

        def fetch_europe_pmc_by_doi(doi: str):
            """Try Europe PMC for DOI; return (title, abstract)."""
            try:
                url_api = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
                params = {
                    'query': f'DOI:{doi}',
                    'format': 'json',
                    'pageSize': 1
                }
                resp = requests.get(url_api, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                hit = (data.get('resultList', {}).get('result') or [])
                hit = hit[0] if hit else None
                if not hit:
                    return None, None
                title_val = hit.get('title') or None
                abstract_val = hit.get('abstractText') or None
                return title_val, abstract_val
            except requests.RequestException:
                return None, None

        doi = extract_doi(url)

        # DOI-first: try PubMed/PMC
        if doi:
            pm_title, pm_abs = fetch_pubmed_by_doi(doi)
            if pm_abs:
                if pm_title and not title:
                    title = pm_title
                full_text = f"{pm_title or title or ''} {pm_abs}".strip()

        # DOI-second: try Europe PMC
        if not full_text and doi:
            epmc_title, epmc_abs = fetch_europe_pmc_by_doi(doi)
            if epmc_abs:
                if epmc_title and not title:
                    title = epmc_title
                full_text = f"{epmc_title or title or ''} {epmc_abs}".strip()

        pubmed_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        if pubmed_match and not full_text:
            pmid = pubmed_match.group(1)
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                eutils_url = (
                    'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
                    f'?db=pubmed&id={pmid}&retmode=xml'
                )
                eutils_response = requests.get(eutils_url, headers=headers, timeout=15)
                eutils_response.raise_for_status()
                xml_soup = BeautifulSoup(eutils_response.text, 'lxml-xml')
                article_title_node = xml_soup.find('ArticleTitle')
                abstract_nodes = xml_soup.find_all('AbstractText')
                article_title_text = (
                    article_title_node.get_text(' ', strip=True)
                    if article_title_node else ''
                )
                abstract_text = ' '.join(
                    node.get_text(' ', strip=True) for node in abstract_nodes
                )
                if not title and article_title_text:
                    title = article_title_text
                full_text = ' '.join(
                    part for part in [article_title_text, abstract_text] if part
                ).strip()
            except requests.RequestException as e:
                return JsonResponse({
                    'error': f'Failed to fetch PubMed content via E-utilities: {str(e)}'
                }, status=500)

        if not full_text:
            # Fetch the webpage content
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                try:
                    response.raise_for_status()
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 500
                    if status in (401, 403):
                        # Try to extract DOI from URL and fetch from alternative sources
                        doi_from_url = extract_doi(url)
                        if doi_from_url:
                            pm_title_retry, pm_abs_retry = fetch_pubmed_by_doi(doi_from_url)
                            if pm_abs_retry:
                                if pm_title_retry and not title:
                                    title = pm_title_retry
                                full_text = f"{pm_title_retry or title or ''} {pm_abs_retry}".strip()
                            else:
                                epmc_title_retry, epmc_abs_retry = fetch_europe_pmc_by_doi(doi_from_url)
                                if epmc_abs_retry:
                                    if epmc_title_retry and not title:
                                        title = epmc_title_retry
                                    full_text = f"{epmc_title_retry or title or ''} {epmc_abs_retry}".strip()
                        
                        # If still no content, return helpful error
                        if not full_text:
                            return JsonResponse({
                                'error': 'This article is behind a paywall or requires authentication. Try searching for the article title in Google Scholar or PubMed for open-access versions, or use the article\'s DOI with Sci-Hub or institutional access.'
                            }, status=403)
                    return JsonResponse({
                        'error': f'Failed to fetch the webpage (HTTP {status}). The content may require authentication or be temporarily unavailable.'
                    }, status=502)
            except requests.RequestException as e:
                return JsonResponse({
                    'error': f'Network error while fetching webpage: {str(e)}. Please check the URL and try again.'
                }, status=502)

            # Extract text content from HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                script.decompose()

            # Get text from main content areas (common tags for article content)
            main_content = soup.find_all(['article', 'main', 'section', 'p', 'div'])
            text_parts = []

            for element in main_content:
                text = element.get_text(separator=' ', strip=True)
                if len(text) > 50:  # Only include substantial text blocks
                    text_parts.append(text)

            # Join and clean the text
            full_text = ' '.join(text_parts)
            full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
        
        # Limit text to reasonable length for AI processing (first ~8000 chars)
        if len(full_text) > 8000:
            full_text = full_text[:8000] + "..."
        
        # If content is insufficient, try to use snippet as fallback
        title_only_mode = False
        if len(full_text) < 100:
            if snippet and len(snippet) > 50:
                full_text = f"{title}\n\n{snippet}"
                logger.info("Using snippet as fallback for content extraction")
            else:
                # Last resort: generate brief summary from title only
                title_only_mode = True
                full_text = title
                logger.info("Generating brief summary from title only (content inaccessible)")
        
        # Generate AI summary
        if title_only_mode:
            # Brief 5-line summary based on title only
            prompt = f"""The research paper titled "{title}" is inaccessible due to authentication requirements or paywall restrictions.

Based on the title alone, provide a brief, informative 5-line explanation of what this research is likely about. Include:
1. The main research topic or focus area
2. Potential scope and objectives
3. Relevance to the field
4. Possible methodologies or approaches
5. Expected significance or applications

Keep it concise (exactly 5 bullet points) and factual. Start each line with "•"."""
        else:
            # Comprehensive summary with full content
            prompt = f"""You are analyzing a research paper. Generate a comprehensive summary in 8-10 distinct bullet points.

Title: {title}

Full Content:
{full_text}

Create a detailed summary with these bullet points:
- Research objective and hypothesis
- Key methodology used
- Main findings and results
- Statistical significance or data analysis
- Relevance to drug discovery or molecular research
- Potential therapeutic applications
- Study limitations or future directions
- Any novel compounds or targets identified

Format each point starting with "•" or "-" and make each point clear and informative."""

        # Call Ollama AI
        try:
            ollama_response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': 'gemma3:4b',
                    'messages': [
                        {'role': 'system', 'content': 'You are a research paper summarization assistant. Provide clear, factual bullet-point summaries.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'stream': False
                },
                timeout=60  # Longer timeout for paper processing
            )
            
            if ollama_response.status_code == 200:
                result = ollama_response.json()
                ai_message = result.get('message', {}).get('content', 'No response generated')
                
                # Convert Markdown to HTML
                html_content = markdown.markdown(
                    ai_message,
                    extensions=['extra', 'nl2br']
                )
                
                # Sanitize HTML
                safe_html = bleach.clean(
                    html_content,
                    tags=['p', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'h1', 'h2', 'h3', 'span', 'div', 'i'],
                    attributes={'div': ['class'], 'i': ['class'], 'span': ['class']},
                    strip=True
                )
                
                # Add disclaimer for title-only summaries
                if title_only_mode:
                    disclaimer = '<div class="alert alert-warning border-0 mb-3"><i class="fas fa-info-circle me-2"></i><strong>Limited Access:</strong> Full content unavailable due to authentication/paywall. This summary is inferred from the title only.</div>'
                    safe_html = disclaimer + safe_html
                
                return JsonResponse({
                    'success': True,
                    'summary': safe_html,
                    'title_only': title_only_mode
                })
            else:
                return JsonResponse({
                    'error': 'AI service returned an error'
                }, status=500)
                
        except requests.exceptions.RequestException:
            return JsonResponse({
                'error': 'AI service (Ollama) is not available. Please ensure Ollama is running with gemma3:4b model.'
            }, status=503)
            
    except Exception as e:
        logger.error(f"Error in summarize_research_paper: {e}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)
