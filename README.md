# Drug Discovery Platform

Full-stack Django and DRF project for storing molecules, running cheminformatics analyses, and using local or cloud LLMs for drug discovery workflows.

## What you get
- Molecule knowledge base with CRUD APIs, SMILES validation, automatic formulas/weights, 2D image generation, and PDB lookups (RCSB).
- Predictive services: rule-based RDKit descriptors, scikit-learn heuristics, and optional Ollama (Gemma3) for toxicity, solubility, bioavailability, and layman explanations.
- AI insights: OpenFDA and PubChem data are summarized through local LLMs; optional OpenAI support is wired via environment variables.
- Visualization layer: search, detail view with 3D coordinates, compound analyzer canvas, AI chat, and dataset statistics.
- Admin and audit: dashboard with activity logs, search analytics, export to JSON/CSV/XLSX, and user preferences.
- Security: custom user model, Django Allauth (Google/GitHub), optional email verification, reCAPTCHA, OTP-based 2FA, and brute-force protection via django-axes.
- Background tasks: Celery + Redis ready for asynchronous jobs and notifications.

## App map
- Backend configuration: config/settings.py and config/urls.py
- Molecule APIs and utilities: apps/molecules (RDKit processing, PDB search, SMILES analyzer, ML SMILES generator)
- Prediction services: apps/neural_networks (descriptor models and Ollama predictors)
- Visualization and UI pages: apps/visualization (search, details, AI chat, stats)
- Admin dashboard: apps/admin_dashboard (activity logging, exports, support tools)
- Authentication: apps/authentication (custom user, OAuth, 2FA, reCAPTCHA)

## Quick start
1) Requirements: Python 3.11+, Git, Redis (for Celery/background jobs), and optionally Ollama for local LLMs.
2) Setup the environment:
```
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```
3) Configure environment variables (.env at project root):
```
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=dd3s.sup@gmail.com

RECAPTCHA_PUBLIC_KEY=
RECAPTCHA_PRIVATE_KEY=
GOOGLE_API_KEY=
GOOGLE_CSE_ID=
OPENAI_API_KEY=
OPENALEX_API_KEY=
OPENALEX_MAILTO=
CORE_API_KEY=
REDIS_URL=redis://localhost:6379
```
4) Apply migrations and create a superuser:
```
python manage.py migrate
python manage.py createsuperuser
```
5) (Optional) Load the bundled dataset after migrations:
```
python import_batches.py
```
   The script imports balanced batches from ALL_7_Gene_SMILES_isActive.json and skips duplicates.
6) Run the server:
```
python manage.py runserver 8000
```
7) Visit the app at http://127.0.0.1:8000 and the API at http://127.0.0.1:8000/api/.

## Local LLM and GPU notes
- Ollama: install from https://ollama.com/download, then `ollama pull gemma3:4b`. Keep Ollama running to enable local toxicity/solubility and layman summaries.
- PyTorch GPU: for CUDA wheels run `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126` (use cu128 if your driver supports 12.8). Verify with `python test_gpu_setup.py`.

## Helpful scripts and endpoints
- REST endpoints: see apps/molecules/urls.py and apps/neural_networks/urls.py for search, SMILES validation, property calculations, PDB lookups, and predictions by molecule id or raw SMILES.
- Dataset import: import_batches.py loads 300 molecules per target in multiple batches; sample data lives in ALL_7_Gene_SMILES_isActive.json.
- Admin dashboard: /admin-dashboard/ for user analytics, exports, and preferences; standard Django admin at /admin/.

## Windows: 2D rendering fix
- If the compound analyzer shows "2D structure rendering not available", add an exclusion for `.venv` in Windows Security and restart the server.
- Run `python check_rdkit_backend.py` to confirm the available RDKit backend; for a full guide see FIX_WINDOWS_2D_RENDERING.md.
