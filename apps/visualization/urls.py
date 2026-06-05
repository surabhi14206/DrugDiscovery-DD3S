from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'visualization'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    path('search/', views.search, name='search'),
    path('design/', views.design, name='design'),
    path('molecule/<int:pk>/', views.molecule_detail, name='molecule_detail'),
    path('molecules/<int:pk>/', views.molecule_detail, name='molecule_detail_plural'),  # Allow plural form
    path('api/get-pdb-from-smiles/', views.get_pdb_from_smiles, name='get_pdb_from_smiles'),
    path('api/chat-with-ai/', views.chat_with_ai, name='chat_with_ai'),
    path('api/calculate-properties/', views.calculate_properties, name='calculate_properties'),
    path('api/drug-likeness-metrics/', views.get_drug_likeness_metrics, name='get_drug_likeness_metrics'),
    path('api/database-stats/', views.get_database_stats, name='get_database_stats'),
    path('api/ai-insights/', views.get_ai_insights, name='get_ai_insights'),
    path('api/web-search/', views.web_search_proxy, name='web_search_proxy'),
    path('search/summary/', views.summary_view, name='search_summary'),
    path('api/summarize-paper/', views.summarize_research_paper, name='summarize_paper'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    # path('terms/', views.terms, name='terms'),  # TODO: Implement this view
    path('test-theme/', TemplateView.as_view(template_name='test_theme.html'), name='test_theme'),
]
