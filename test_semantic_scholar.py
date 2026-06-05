import requests
import json

def test_semantic_scholar():
    query = "Aspirin"
    sem_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {
        'User-Agent': 'MolecularDatabaseApp/1.0 (research_demo@example.com)'
    }
    sem_params = {
        "query": query,
        "limit": 5,
        "fields": "title,authors,year,venue,abstract,url,paperId"
    }
    
    print(f"Testing Semantic Scholar API with query: {query}")
    try:
        sem_resp = requests.get(sem_url, headers=headers, params=sem_params, timeout=10)
        print(f"Status Code: {sem_resp.status_code}")
        
        if sem_resp.status_code == 200:
            data = sem_resp.json()
            count = len(data.get("data", []))
            print(f"Success! Found {count} papers.")
            if count > 0:
                print("First paper title:", data["data"][0].get("title"))
        else:
            print("Failed.")
            print("Response:", sem_resp.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_semantic_scholar()
