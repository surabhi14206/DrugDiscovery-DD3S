from rest_framework import serializers
from .models import Molecule, MoleculeProperty


class MoleculePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoleculeProperty
        fields = '__all__'


class MoleculeSerializer(serializers.ModelSerializer):
    properties = MoleculePropertySerializer(many=True, read_only=True)
    
    # Add computed fields for drug properties
    esol_solubility = serializers.SerializerMethodField()
    structural_alerts = serializers.SerializerMethodField()
    lipinski_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = Molecule
        fields = '__all__'
    
    def get_esol_solubility(self, obj):
        """Include ESOL solubility if available"""
        try:
            return obj.get_esol_solubility()
        except:
            return None
    
    def get_structural_alerts(self, obj):
        """Include structural alerts if available"""
        try:
            return obj.get_structural_alerts()
        except:
            return None
    
    def get_lipinski_profile(self, obj):
        """Include Lipinski profile if available"""
        try:
            return obj.get_lipinski_profile()
        except:
            return None

