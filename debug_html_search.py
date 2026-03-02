
import re

file_path = r"d:\K\3K Sunoty\debug_filter_page.html"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    matches = [m.start() for m in re.finditer(r"Filter", content, re.IGNORECASE)]
    
    print(f"Found {len(matches)} matches for 'Filter'")
    
    for i, pos in enumerate(matches):
        start = max(0, pos - 100)
        end = min(len(content), pos + 100)
        snippet = content[start:end]
        print(f"\nMatch {i+1}:")
        print(snippet)
        if i >= 4: # Print only first 5
            break
            
except Exception as e:
    print(f"Error: {e}")
