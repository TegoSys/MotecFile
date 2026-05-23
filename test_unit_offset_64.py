from motec_parser import read_ldfile

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    with open(file_path, 'rb') as f:
        for i in range(10):
            chan = chans[i]
            f.seek(chan.meta_ptr + 64) # Jump to offset 64 (32 for name + 32)
            unit_candidate = f.read(12).rstrip(b'\x00')
            print(f"Chan {i} ({chan.name}): Unit candidate at offset 64: {unit_candidate}")
except Exception as e:
    print(f"Error: {e}")
