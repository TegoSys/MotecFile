import struct
import numpy as np
import pandas as pd
from motec_parser import read_ldfile, decode_string

file_path = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'

try:
    head, chans = read_ldfile(file_path)
    print(f"Total channels: {len(chans)}")

    # Print raw bytes for the first 20 channels' units
    for i, chan in enumerate(chans[:20]):
        # We need to get the raw bytes. Since ldChan.fromfile doesn't store them,
        # we'll manually read from the file using the chan's meta_ptr.
        with open(file_path, 'rb') as f:
            f.seek(chan.meta_ptr)
            # ldChan.fmt is the format. We want the 'unit' part.
            # fmt = 'IIII' (16) + 'H' (2) + 'HHH' (6) + 'hhhh' (8) + '32s' (32) + '8s' (8) + '12s' (12)
            # Total before unit: 16+2+6+8+32+8 = 72 bytes.
            f.seek(chan.meta_ptr + 72)
            unit_bytes = f.read(12)
            print(f"Chan {i} ({chan.name}): Raw Units Bytes: {unit_bytes} | Decoded: {decode_string(unit_bytes)}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
