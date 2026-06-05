from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'molecules'

# Use SimpleRouter instead of DefaultRouter to avoid API root view
router = SimpleRouter()
router.register(r'molecules', views.MoleculeViewSet, basename='molecule')

urlpatterns = router.urls + [
    path('search/', views.search_molecules, name='search'),
    path('predict/toxicity/<int:molecule_id>/', views.predict_toxicity, name='predict_toxicity'),
    path('predict/solubility/<int:molecule_id>/', views.predict_solubility, name='predict_solubility'),
    path('predict/activity/<int:molecule_id>/', views.predict_activity, name='predict_activity'),
    
    # Molecular property calculation endpoints
    path('calculate-properties/', views.calculate_properties, name='calculate_properties'),
    path('validate-smiles/', views.validate_smiles_api, name='validate_smiles'),
    path('sanitize-smiles/', views.sanitize_smiles_api, name='sanitize_smiles'),
    
    # 3D structure generation
    path('generate-3d/', views.generate_3d_structure, name='generate_3d'),
    
    # ML SMILES generation
    path('generate-ml-smiles/', views.generate_ml_smiles_api, name='generate_ml_smiles'),
    
    # PDB lookup endpoints
    path('lookup-pdb/', views.lookup_pdb_id, name='lookup_pdb'),
    path('search-pdb-target/', views.search_pdb_by_target, name='search_pdb_target'),
    
    # AI explanation endpoint
    path('ai-explanation/<int:molecule_id>/', views.generate_ai_explanation, name='ai_explanation'),
    
    # Compound analyzer
    path('analyzer/', views.compound_analyzer_view, name='compound_analyzer'),
    path('analyze-compound/', views.analyze_compound, name='analyze_compound'),
    
    # Name to SMILES converter with 2D coordinates
    path('name-to-smiles/', views.name_to_smiles, name='name_to_smiles'),
    
    # Molecular structure analysis (multi-molecule support)
    path('analyze-structure/', views.analyze_molecular_structure, name='analyze_structure'),
]
