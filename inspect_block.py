from motec_parser import read_ldfile

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    with open(file_path, 'rb') as f:
        f.seek(head.meta_ptr)
        # Read the entire block containing channel metadata
        block = f.read(head.data_ptr - head.meta_ptr)
        print(f"Metadata block size: {len(block)}")

        # Try to find common unit strings in this block
        search_terms = [b'V', b'rpm', b'kPa', b'mg', b'degC', b'%']
        for term in search_terms:
            idx = block.find(term)
            if idx != -1:
                print(f"Found {term} at offset {idx} from meta_ptr")
            else:
                print(f"Term {term} not found in metadata block")
except Exception as e:
    print(f"Error: {e}")
