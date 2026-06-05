"""
Quick test script to verify Google Custom Search API is working.
Run this to test your API credentials before using in the main app.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

def test_google_search():
    """Test Google Custom Search API with a simple query"""
    
    print("🔍 Testing Google Custom Search API...\n")
    
    # Check if credentials are configured
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("❌ ERROR: API credentials not found in .env file")
        print("   Please add GOOGLE_API_KEY and GOOGLE_CSE_ID to your .env file")
        return False
    
    print(f"✓ API Key found: {GOOGLE_API_KEY[:20]}...")
    print(f"✓ CSE ID found: {GOOGLE_CSE_ID}")
    print()
    
    # Test query
    test_query = "cancer research"
    print(f"📝 Testing search query: '{test_query}'")
    print()
    
    try:
        # Make API request
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'q': f"{test_query} research paper",
            'num': 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if items:
                print(f"✅ SUCCESS! Found {len(items)} results:\n")
                
                for i, item in enumerate(items, 1):
                    print(f"{i}. {item.get('title', 'No title')}")
                    print(f"   URL: {item.get('link', 'No link')}")
                    print(f"   Snippet: {item.get('snippet', 'No snippet')[:100]}...")
                    print()
                
                # Check quota info
                queries = data.get('queries', {})
                request_info = queries.get('request', [{}])[0]
                total_results = request_info.get('totalResults', 'Unknown')
                
                print(f"📊 Total results available: {total_results}")
                print()
                print("✅ Google Custom Search API is working correctly!")
                print("🎉 You can now use the search feature in your application.")
                return True
            else:
                print("⚠️  API call successful but no results returned")
                print("   This might mean your search engine needs configuration")
                return False
                
        elif response.status_code == 429:
            print("❌ ERROR: Rate limit exceeded")
            print("   You've used all 100 free queries for today")
            print("   Wait until tomorrow or upgrade to paid tier")
            return False
            
        elif response.status_code == 403:
            print("❌ ERROR: API key invalid or restricted")
            print("   Response:", response.text)
            print("\n   Troubleshooting:")
            print("   1. Check if Custom Search API is enabled in Google Cloud Console")
            print("   2. Verify your API key is correct")
            print("   3. Make sure API key restrictions allow Custom Search API")
            return False
            
        else:
            print(f"❌ ERROR: API returned status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   Check your internet connection")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("   Google Custom Search API Test")
    print("=" * 60)
    print()
    
    success = test_google_search()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ All tests passed! Your API is ready to use.")
    else:
        print("❌ Tests failed. Please check the errors above.")
        print("\n📖 For help, see: GOOGLE_RESEARCH_SEARCH_SETUP.md")
    
    print("=" * 60)
