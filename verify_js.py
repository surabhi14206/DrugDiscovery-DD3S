
import re
import subprocess
import os

file_path = "c:/Users/yadav/OneDrive/Desktop/DD/templates/visualization/design.html"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract content between <script> and </script> inside extra_js block
# Approximate location based on previous reads
start_marker = "{% block extra_js %}"
end_marker = "{% endblock %}"

start_idx = content.find(start_marker)
end_idx = content.rfind(end_marker) # Use rfind to get the last endblock

if start_idx != -1 and end_idx != -1:
    block_content = content[start_idx:end_idx]
    # Find script tags
    script_start = block_content.find("<script>")
    script_end = block_content.rfind("</script>")
    
    if script_start != -1 and script_end != -1:
        js_content = block_content[script_start + 8 : script_end]
        
        # Write to temp js file
        js_file = "c:/Users/yadav/OneDrive/Desktop/DD/temp_check.js"
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_content)
            
        print(f"Extracted JS to {js_file}. Running syntax check...")
        
        try:
            # Node might not be in path or might need npx, but try node -c
            result = subprocess.run(["node", "-c", js_file], capture_output=True, text=True)
            if result.returncode == 0:
                print("Syntax Check PASSED.")
            else:
                print("Syntax Check FAILED:")
                print(result.stderr)
        except Exception as e:
            print(f"Could not run node: {e}")
    else:
        print("Could not find script tags in extra_js block.")
else:
    print("Could not find extra_js block.")
