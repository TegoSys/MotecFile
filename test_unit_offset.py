from motec_parser import read_ldfile

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    with open(file_path, 'rb') as f:
        for i, chan in enumerate(chans):
            f.seek(chan.meta_ptr + 32) # Jump to end of name
            unit_candidate = f.read(12).rstrip(b'\x00')
            if unit_candidate:
                print(f"Chan {i} ({chan.name}): Unit candidate at offset 32: {unit_candidate}")
except Exception as e:
    print(f"Error: {e}")
