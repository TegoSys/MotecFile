import os

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'
search_units = [b'V', b'rpm', b'degC', b'kPa', b'mg', b'%']

with open(file_path, 'rb') as f:
    content = f.read()

for unit in search_units:
    pos = content.find(unit)
    if pos != -1:
        print(f"Found unit {unit} at position {pos}")
    else:
        print(f"Unit {unit} not found")
