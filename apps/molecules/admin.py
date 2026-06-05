from django.contrib import admin
from .models import Molecule, MoleculeProperty, ImportStatistics


@admin.register(Molecule)
class MoleculeAdmin(admin.ModelAdmin):
    list_display = ['name', 'pdb_id', 'is_active', 'gene_target', 'created_at']
    list_filter = ['is_active', 'gene_target', 'created_at']
    search_fields = ['name', 'pdb_id', 'smiles', 'molecular_formula']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'pdb_id', 'smiles', 'molecular_formula', 'molecular_weight')
        }),
        ('Files', {
            'fields': ('structure_file', 'image_2d')
        }),
        ('Activity', {
            'fields': ('is_active', 'gene_target')
        }),
        ('Predicted Properties', {
            'fields': ('toxicity_score', 'solubility', 'radioactivity', 'bioavailability')
        }),
        ('Metadata', {
            'fields': ('added_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MoleculeProperty)
class MoleculePropertyAdmin(admin.ModelAdmin):
    list_display = ['molecule', 'property_name', 'predicted', 'calculated_at']
    list_filter = ['predicted', 'calculated_at']
    search_fields = ['molecule__name', 'property_name']


@admin.register(ImportStatistics)
class ImportStatisticsAdmin(admin.ModelAdmin):
    list_display = ['source_file', 'total_entries', 'created_count', 'updated_count', 'error_count', 'import_date']
    list_filter = ['import_date']
    search_fields = ['source_file', 'notes']
    readonly_fields = ['import_date']

