from motec_parser import read_ldfile
from collections import Counter

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'
try:
    head, chans = read_ldfile(file_path)
    names = [c.name for c in chans]
    counts = Counter(names)
    duplicates = {name: count for name, count in counts.items() if count > 1}
    print(f"Total channels: {len(names)}")
    print(f"Unique channels: {len(counts)}")
    print(f"Duplicates: {duplicates}")
except Exception as e:
    print(f"Error: {e}")
