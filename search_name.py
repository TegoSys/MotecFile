import os

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'
search_term = b'Brake.State'

with open(file_path, 'rb') as f:
    content = f.read()
    pos = content.find(search_term)
    if pos != -1:
        print(f"Found 'Brake.State' at position {pos}")
        # Print 128 bytes around it
        start = max(0, pos - 64)
        end = min(len(content), pos + 64)
        print(f"Context: {content[start:end]}")
    else:
        print("Brake.State not found")
