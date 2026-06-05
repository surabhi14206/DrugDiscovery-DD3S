
import requests
import time

url = 'http://127.0.0.1:8000/api/web-search/?q=aspirin'
print(f"Testing URL: {url}")

try:
    start = time.time()
    response = requests.get(url, timeout=10)
    print(f"Time taken: {time.time() - start:.2f}s")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data.get('results', []))} results.")
        # print first result title
        if data.get('results'):
            print(f"First result: {data['results'][0]['title']}")
    else:
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")
