from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import requests
import logging
import markdown
import bleach

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
def ai_structure_chat(request):
    """
    API for AI Molecular Assistant chat.
    Accepts molecular context and a user query to provide detailed scientific analysis.
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        context = data.get('context', {})
        
        if not query:
             return JsonResponse({'success': False, 'error': 'No query provided'}, status=400)

        # Construct a detailed context string from the molecule data
        formula = context.get('formula', 'Unknown')
        atom_count = len(context.get('atoms', []))
        bond_count = len(context.get('bonds', []))
        
        # Create a scientifically robust prompt
        system_prompt = f"""You are an advanced AI Molecular Assistant and Chemoinformatics Expert. 
Your goal is to provide deep, scientifically accurate, and elaborate analysis of molecular structures.

Current Molecule Context:
- Formula: {formula}
- Atom Count: {atom_count}
- Bond Count: {bond_count}
- Atoms: {json.dumps(context.get('atoms', []))}
- Bonds: {json.dumps(context.get('bonds', []))}

User Query: "{query}"

INSTRUCTIONS:
1. Provide a DETAILED, MULTI-PARAGRAPH response. Do not be brief.
2. Structure your answer with clear headings or bullet points where appropriate (use Markdown).
3. If asked to VALIDATE: specificially check for valence errors, bond order issues, and steric hindrance. Explain WHY it is valid or invalid using chemical principles.
4. If asked to EXPLAIN: dive into the potential properties (polarity, solubility, reactivity).
5. If asked about HUMAN IMPACT: discuss toxicity, metabolic pathways, and potential biological targets.
6. If asked for IMPROVEMENTS: suggest specific structural modifications to enhance drug-likeness (Lipinski's Rule of 5).

Format your response as a rich scientific report.
"""
        
        # Call Ollama
        ollama_response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'gemma3:4b',
                'prompt': system_prompt,
                'stream': False
            },
            timeout=60 # Increased timeout for elaborate responses
        )

        if ollama_response.status_code == 200:
            result = ollama_response.json()
            summary = result.get('response', 'Failed to generate analysis.')
            
            # Render Markdown to HTML for the frontend
            html_content = markdown.markdown(
                summary.strip(),
                extensions=['extra', 'fenced_code', 'tables', 'nl2br']
            )
            
            # Sanitize
            allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + [
                'p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'code', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
            ]
            sanitized_html = bleach.clean(html_content, tags=allowed_tags, strip=True)

            return JsonResponse({
                'success': True,
                'response': summary,
                'response_html': sanitized_html
            })
        else:
             return JsonResponse({
                'success': False,
                'error': f'Ollama Error: {ollama_response.status_code}'
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"AI Structure Chat error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
