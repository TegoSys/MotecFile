import os

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'
search_term = b'Coolant.Temperature'

with open(file_path, 'rb') as f:
    content = f.read()
    pos = content.find(search_term)
    if pos != -1:
        print(f"Found 'Coolant.Temperature' at position {pos}")
        start = max(0, pos - 64)
        end = min(len(content), pos + 64)
        print(f"Context: {content[start:end]}")
    else:
        print("Coolant.Temperature not found")
