"""
URL configuration for neural network predictions
"""
from django.urls import path
from . import views

app_name = 'neural_networks'

urlpatterns = [
    # Predictions by molecule ID
    path('predict/toxicity/<int:molecule_id>/', views.predict_toxicity, name='predict_toxicity'),
    path('predict/solubility/<int:molecule_id>/', views.predict_solubility, name='predict_solubility'),
    path('predict/drug-likeness/<int:molecule_id>/', views.predict_drug_likeness, name='predict_drug_likeness'),
    path('predict/bioactivity/<int:molecule_id>/', views.predict_bioactivity, name='predict_bioactivity'),
    path('predict/all/<int:molecule_id>/', views.predict_all, name='predict_all'),
    
    # Predictions by SMILES (POST or GET with ?smiles=...)
    path('predict/toxicity/', views.predict_toxicity, name='predict_toxicity_smiles'),
    path('predict/solubility/', views.predict_solubility, name='predict_solubility_smiles'),
    path('predict/drug-likeness/', views.predict_drug_likeness, name='predict_drug_likeness_smiles'),
    path('predict/bioactivity/', views.predict_bioactivity, name='predict_bioactivity_smiles'),
    path('predict/all/', views.predict_all, name='predict_all_smiles'),
]
