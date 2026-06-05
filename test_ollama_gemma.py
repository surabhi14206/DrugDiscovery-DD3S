"""
Test Ollama connection and Gemma 3:4b model
"""
import requests
import json

def test_ollama():
    print("Testing Ollama connection...")
    
    # Test 1: Check if Ollama is running
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running!")
            models = response.json().get('models', [])
            print(f"\nAvailable models ({len(models)}):")
            for model in models:
                print(f"  - {model['name']}")
            
            # Check if gemma3:4b is available
            gemma_found = any('gemma3:4b' in model['name'] for model in models)
            if gemma_found:
                print("\n✅ gemma3:4b is installed!")
            else:
                print("\n❌ gemma3:4b NOT found!")
                print("To install: ollama pull gemma3:4b")
                return False
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("\nPlease ensure:")
        print("1. Ollama is installed")
        print("2. Ollama app is running")
        return False
    
    # Test 2: Test chat with gemma3:4b
    print("\n" + "="*50)
    print("Testing gemma3:4b chat...")
    try:
        chat_response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': 'gemma3:4b',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'What is the molecular formula of ethanol?'
                    }
                ],
                'stream': False
            },
            timeout=30
        )
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            message = result.get('message', {}).get('content', '')
            print("✅ Gemma3:4b responded!")
            print(f"\nResponse: {message[:200]}...")
            return True
        else:
            print(f"❌ Chat failed with status {chat_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama()
    print("\n" + "="*50)
    if success:
        print("✅ All tests passed! Gemma3:4b is ready to use.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
