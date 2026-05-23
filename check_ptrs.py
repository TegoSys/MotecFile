from motec_parser import read_ldfile

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    print(f"Meta Ptr: {head.meta_ptr}")
    print(f"Data Ptr: {head.data_ptr}")
    print(f"Num Chans: {len(chans)}")
    if chans:
        print(f"First Chan Meta Ptr: {chans[0].meta_ptr}")
        print(f"First Chan Name: {chans[0].name}")
        print(f"First Chan Unit: {chans[0].unit}")
except Exception as e:
    print(f"Error: {e}")
