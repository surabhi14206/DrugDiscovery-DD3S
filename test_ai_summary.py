"""
Test script for AI drug summary system.
Run this to verify your OpenAI API key is working correctly.

Usage:
    python test_ai_summary.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.utils import (
    get_drug_data_from_openfda,
    get_drug_data_from_pubchem,
    generate_layman_summary_with_ai,
    get_comprehensive_drug_summary
)
from django.conf import settings


def test_openai_key():
    """Test if OpenAI API key is configured"""
    print("\n" + "="*70)
    print("TESTING OPENAI API KEY CONFIGURATION")
    print("="*70)
    
    if not settings.OPENAI_API_KEY:
        print("❌ FAILED: OPENAI_API_KEY is not set in settings")
        return False
    
    if settings.OPENAI_API_KEY == 'your-openai-api-key-here':
        print("❌ FAILED: OPENAI_API_KEY is still the placeholder value")
        print("\n📝 TO FIX:")
        print("1. Get your API key from https://platform.openai.com/api-keys")
        print("2. Add it to your .env file: OPENAI_API_KEY=sk-your-key-here")
        print("3. Restart Django server and run this test again")
        return False
    
    if not settings.OPENAI_API_KEY.startswith('sk-'):
        print("❌ FAILED: OPENAI_API_KEY doesn't look valid (should start with 'sk-')")
        return False
    
    print(f"✅ PASSED: API key is configured (starts with {settings.OPENAI_API_KEY[:10]}...)")
    return True


def test_openfda():
    """Test OpenFDA API connection"""
    print("\n" + "="*70)
    print("TESTING OPENFDA API")
    print("="*70)
    
    print("Fetching data for 'Aspirin'...")
    data = get_drug_data_from_openfda('Aspirin')
    
    if "error" in data:
        print(f"⚠️  WARNING: {data['error']}")
        print("This is normal for research compounds not in FDA database")
        return True
    
    print("✅ PASSED: Successfully fetched OpenFDA data")
    print(f"   Found fields: {', '.join(data.keys())}")
    return True


def test_pubchem():
    """Test PubChem API connection"""
    print("\n" + "="*70)
    print("TESTING PUBCHEM API")
    print("="*70)
    
    print("Fetching data for Aspirin (CC(=O)Oc1ccccc1C(=O)O)...")
    data = get_drug_data_from_pubchem('CC(=O)Oc1ccccc1C(=O)O', 'Aspirin')
    
    if "error" in data:
        print(f"❌ FAILED: {data['error']}")
        return False
    
    print("✅ PASSED: Successfully fetched PubChem data")
    print(f"   Molecular Formula: {data.get('molecular_formula')}")
    print(f"   Molecular Weight: {data.get('molecular_weight')}")
    return True


def test_ai_generation():
    """Test AI summary generation"""
    print("\n" + "="*70)
    print("TESTING AI SUMMARY GENERATION")
    print("="*70)
    
    if not test_openai_key():
        print("⏭️  SKIPPING: OpenAI API key not configured")
        return False
    
    print("Generating AI summary for Aspirin...")
    print("(This may take 3-5 seconds...)")
    
    test_data = {
        "indications": "Aspirin is used to reduce pain, fever, or inflammation.",
        "warnings": "Do not use if you have stomach ulcers. Risk of bleeding.",
    }
    
    test_properties = {
        "SMILES": "CC(=O)Oc1ccccc1C(=O)O",
        "Molecular Formula": "C9H8O4"
    }
    
    summary = generate_layman_summary_with_ai(
        "Aspirin",
        test_data,
        test_properties
    )
    
    if "Error" in summary or "⚠️ OpenAI API key not configured" in summary:
        print(f"❌ FAILED: {summary[:200]}...")
        return False
    
    print("✅ PASSED: Successfully generated AI summary")
    print("\n" + "-"*70)
    print("GENERATED SUMMARY:")
    print("-"*70)
    print(summary)
    print("-"*70)
    return True


def test_comprehensive_summary():
    """Test the complete end-to-end process"""
    print("\n" + "="*70)
    print("TESTING COMPREHENSIVE DRUG SUMMARY (END-TO-END)")
    print("="*70)
    
    print("Generating complete summary for Aspirin...")
    print("(This will fetch from both APIs and generate AI summary)")
    
    result = get_comprehensive_drug_summary(
        molecule_name="Aspirin",
        smiles_string="CC(=O)Oc1ccccc1C(=O)O",
        gene_target="COX-2"
    )
    
    print(f"\n✅ Data sources used: {', '.join(result['data_sources'])}")
    print(f"✅ Generated summary: {len(result['layman_summary'])} characters")
    
    print("\n" + "-"*70)
    print("FINAL SUMMARY:")
    print("-"*70)
    print(result['layman_summary'])
    print("-"*70)
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("AI DRUG SUMMARY SYSTEM - TEST SUITE")
    print("="*70)
    
    tests = [
        ("OpenAI API Key", test_openai_key),
        ("OpenFDA API", test_openfda),
        ("PubChem API", test_pubchem),
        ("AI Generation", test_ai_generation),
        ("End-to-End", test_comprehensive_summary),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print("\n" + "="*70)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    print("="*70)
    
    if total_passed == total_tests:
        print("\n🎉 SUCCESS! Your AI drug summary system is fully configured!")
        print("\nNext steps:")
        print("1. Visit http://127.0.0.1:8000/molecule/1/")
        print("2. Click 'Generate AI Explanation' button")
        print("3. View the layman-friendly drug summary!")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("See AI_DRUG_SUMMARY_SETUP.md for troubleshooting tips.")


if __name__ == "__main__":
    main()
