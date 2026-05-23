from motec_parser import read_ldfile

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    with open(file_path, 'rb') as f:
        for i in range(5):
            chan = chans[i]
            f.seek(chan.meta_ptr)
            data = f.read(124)
            name = data[46:78]
            short_name = data[78:86]
            unit = data[86:98]
            print(f"Chan {i}: Name={name}, Short={short_name}, Unit={unit}")
except Exception as e:
    print(f"Error: {e}")
