import json
import numpy as np
import pandas as pd
import os
import struct
import datetime

def decode_string(bytes_val):
    """decode the bytes and remove trailing zeros"""
    try:
        return bytes_val.decode('ascii').strip().rstrip('\0').strip()
    except Exception as e:
        print("Could not decode string: %s - %s" % (e, bytes_val))
        return ""

class ldVehicle(object):
    fmt = '<64s128xI32s32s'
    def __init__(self, id, weight, type, comment):
        self.id, self.weight, self.type, self.comment = id, weight, type, comment

    @classmethod
    def fromfile(cls, f):
        id, weight, type, comment = struct.unpack(ldVehicle.fmt, f.read(struct.calcsize(ldVehicle.fmt)))
        id, type, comment = map(decode_string, [id, type, comment])
        return cls(id, weight, type, comment)

class ldVenue(object):
    fmt = '<64s1034xH'
    def __init__(self, name, vehicle_ptr, vehicle):
        self.name, self.vehicle_ptr, self.vehicle = name, vehicle_ptr, vehicle

    @classmethod
    def fromfile(cls, f):
        name, vehicle_ptr = struct.unpack(ldVenue.fmt, f.read(struct.calcsize(ldVenue.fmt)))
        vehicle = None
        if vehicle_ptr > 0:
            f.seek(vehicle_ptr)
            vehicle = ldVehicle.fromfile(f)
        return cls(decode_string(name), vehicle_ptr, vehicle)

class ldEvent(object):
    fmt = '<64s64s1024sH'
    def __init__(self, name, session, comment, venue_ptr, venue):
        self.name, self.session, self.comment, self.venue_ptr, self.venue = \
            name, session, comment, venue_ptr, venue

    @classmethod
    def fromfile(cls, f):
        name, session, comment, venue_ptr = struct.unpack(
            ldEvent.fmt, f.read(struct.calcsize(ldEvent.fmt)))
        name, session, comment = map(decode_string, [name, session, comment])
        venue = None
        if venue_ptr > 0:
            f.seek(venue_ptr)
            venue = ldVenue.fromfile(f)
        return cls(name, session, comment, venue_ptr, venue)

class ldHead(object):
    fmt = '<' + (
        "I4x"     # ldmarker
        "II"      # chann_meta_ptr chann_data_ptr
        "20x"     # ??
        "I"       # event_ptr
        "24x"     # ??
        "HHH"     # unknown static (?) numbers
        "I"       # device serial
        "8s"      # device type
        "H"       # device version
        "H"       # unknown static (?) number
        "I"       # num_channs
        "4x"     # ??
        "16s"     # date
        "16x"     # ??
        "16s"     # time
        "16x"     # ??
        "64s"     # driver
        "64s"     # vehicleid
        "64x"     # ??
        "64s"     # venue
        "64x"     # ??
        "1024x"   # ??
        "I"       # enable "pro logging" (some magic number?)
        "66x"     # ??
        "64s"     # short comment
        "126x"    # ??
    )

    def __init__(self, meta_ptr, data_ptr, event_ptr, event, driver, vehicleid, venue, datetime, short_comment):
        self.meta_ptr, self.data_ptr, self.event_ptr, self.event, self.driver, self.vehicleid, \
        self.venue, self.datetime, self.short_comment = meta_ptr, data_ptr, event_ptr, event, \
                                                       driver, vehicleid, venue, datetime, short_comment

    @classmethod
    def fromfile(cls, f):
        (_, meta_ptr, data_ptr, event_ptr,
            _, _, _,
            _, _, _, _, n,
            date, time,
            driver, vehicleid, venue,
            _, short_comment) = struct.unpack(ldHead.fmt, f.read(struct.calcsize(ldHead.fmt)))
        date, time, driver, vehicleid, venue, short_comment = \
            map(decode_string, [date, time, driver, vehicleid, venue, short_comment])

        try:
            _datetime = datetime.datetime.strptime(
                    '%s %s'%(date, time), '%d/%m/%Y %H:%M:%S')
        except ValueError:
            _datetime = datetime.datetime.strptime(
                '%s %s'%(date, time), '%d/%m/%Y %H:%M')

        event = None
        if event_ptr > 0:
            f.seek(event_ptr)
            event = ldEvent.fromfile(f)
        return cls(meta_ptr, data_ptr, event_ptr, event, driver, vehicleid, venue, _datetime, short_comment)

class ldChan(object):
    fmt = '<' + (
        "IIII"    # prev_addr next_addr data_ptr n_data
        "H"       # some counter?
        "HHH"     # datatype datatype rec_freq
        "hhhh"    # shift mul scale dec_places
        "32s"     # name
        "12s"     # unit
        "40x"     # ?
    )

    def __init__(self, _f, meta_ptr, prev_meta_ptr, next_meta_ptr, data_ptr, data_len,
                 dtype, freq, shift, mul, scale, dec,
                 name, unit):
        self._f = _f
        self.meta_ptr = meta_ptr
        self._data = None

        (self.prev_meta_ptr, self.next_meta_ptr, self.data_ptr, self.data_len,
        self.dtype, self.freq,
        self.shift, self.mul, self.scale, self.dec,
        self.name, self.unit) = prev_meta_ptr, next_meta_ptr, data_ptr, data_len,\
                                                 dtype, freq,\
                                                 shift, mul, scale, dec,\
                                                 name, unit

    @classmethod
    def fromfile(cls, _f, meta_ptr):
        with open(_f, 'rb') as f:
            f.seek(meta_ptr)
            (prev_meta_ptr, next_meta_ptr, data_ptr, data_len, _,
             dtype_a, dtype, freq, shift, mul, scale, dec,
             name, unit) = struct.unpack(ldChan.fmt, f.read(struct.calcsize(ldChan.fmt)))

        name, unit = map(decode_string, [name, unit])

        def safe_get(lst, idx):
            if idx < 0 or idx >= len(lst):
                return None
            return lst[idx]

        if dtype_a in [0x07]:
            dtype = safe_get([None, np.float16, None, np.float32], dtype - 1)
        elif dtype_a in [0, 0x03, 0x05]:
            dtype = safe_get([None, np.int16, None, np.int32], dtype - 1)
        elif dtype_a == 0x08 and dtype == 0x08:
            dtype = np.dtype('<d')
        else:
            dtype = None

        return cls(_f, meta_ptr, prev_meta_ptr, next_meta_ptr, data_ptr, data_len,
                   dtype, freq, shift, mul, scale, dec, name, unit)

    @property
    def data(self):
        if self.dtype is None:
            return np.full(self.data_len, np.nan)
        if self._data is None:
            with open(self._f, 'rb') as f:
                f.seek(self.data_ptr)
                self._data = np.fromfile(f, count=self.data_len, dtype=self.dtype)
                self._data = (self._data / self.scale * pow(10., -self.dec) + self.shift) * self.mul
        return self._data

def _build_column_name_mapping():
    """Load column name mappings from columnMap.json (63 special-case entries)."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'columnMap.json')
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {json_path} not found, using column names as-is.")
        return {}

def read_channels(f_, meta_ptr):
    chans = []
    while meta_ptr:
        chan_ = ldChan.fromfile(f_, meta_ptr)
        chans.append(chan_)
        meta_ptr = chan_.next_meta_ptr
    return chans

def read_ldfile(f_):
    with open(f_, 'rb') as f:
        head_ = ldHead.fromfile(f)
    chans = read_channels(f_, head_.meta_ptr)
    return head_, chans

class MotecLdParser:
    """
    Refactored Parser for MoTeC .ld binary files.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.head = None
        self.channels = []
        self.df = None

    def parse(self):
        """
        Parses the binary file using pointer-based navigation and extracts scaled data.
        """
        print(f"Parsing MoTeC file: {self.file_path}...")
        self.head, self.channels = read_ldfile(self.file_path)

        num_channels = len(self.channels)
        print(f"Discovered {num_channels} channels.")

        # Determine the maximum data length across all channels (from highest-frequency channels)
        max_data_len = max(chan.data_len for chan in self.channels)
        max_freq = max(chan.freq for chan in self.channels) if any(chan.freq > 0 for chan in self.channels) else 1

        # Extract scaled data for each channel, expanding lower-frequency channels
        # by repeating each sample to fill the full DataFrame length (step-hold behavior).
        # This prevents pandas NaN-padding when channels have different sample counts.
        data_dict = {}
        seen_names = {}

        for chan in self.channels:
            name = chan.name
            if name in seen_names:
                seen_names[name] += 1
                unique_name = f"{name}_{seen_names[name]}"
            else:
                seen_names[name] = 0
                unique_name = name

            raw_data = chan.data
            data_len = chan.data_len

            if data_len < max_data_len and chan.freq > 0:
                repeat_count = max_freq // chan.freq
                expanded = np.repeat(raw_data, repeat_count)
            else:
                expanded = raw_data

            # Trim to max_data_len; if still short, pad with NaN
            if len(expanded) > max_data_len:
                expanded = expanded[:max_data_len]
            elif len(expanded) < max_data_len:
                expanded = np.pad(expanded, (0, max_data_len - len(expanded)), constant_values=np.nan)

            data_dict[unique_name] = expanded

        # Create DataFrame
        self.df = pd.DataFrame(data_dict)

        # Coerce all columns to numeric and fill NaN with 0
        for col in self.df.columns:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)

        print(f"Data successfully loaded and scaled into DataFrame ({self.df.shape[1]} columns).")
        return self.df

    def to_csv(self, output_path):
        """
        Exports the parsed DataFrame to a CSV file with a metadata header and units row.
        """
        if self.df is None or self.head is None:
            raise ValueError("No data parsed. Call parse() first.")

        print(f"Exporting to {output_path}...")

        # Create a copy of the dataframe to avoid modifying the original parser state
        df_copy = self.df.copy()

        # Generate time array: 0.00, 0.01, 0.02... and insert as the first column
        time_array = np.arange(len(df_copy)) * 0.01
        df_copy.insert(0, 'Time', time_array)

        # Extract metadata
        driver = self.head.driver
        vehicleid = self.head.vehicleid
        venue = self.head.venue
        event = self.head.event.name if self.head.event else "N/A"
        session = self.head.event.session if self.head.event else "N/A"
        short_comment = self.head.short_comment

        # Calculate maximum sample rate
        freqs = [chan.freq for chan in self.channels]
        max_freq = max(freqs) if freqs else "N/A"

        # Get units for all channels discovered, matching the DataFrame columns
        units = []
        seen_names = {}
        for chan in self.channels:
            name = chan.name
            if name in seen_names:
                seen_names[name] += 1
                # The name in df is f"{name}_{seen_names[name]}"
            else:
                seen_names[name] = 0
            units.append(chan.unit)

        # Add 's' as the first element of the units row for the Time column
        units.insert(0, 's')

        # Write metadata header then headers, units, and data
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(f'"Format","MoTeC CSV File",,,"Workbook",""\n')
            f.write(f"driver:,    {driver}\n")
            f.write(f"vehicleid:, {vehicleid}\n")
            f.write(f"venue:,     {venue}\n")
            f.write(f"event:,     {event}\n")
            f.write(f"session:,   {session}\n")
            f.write(f"sample rate:, {max_freq} Hz\n")
            f.write(f"short_comment:, {short_comment}\n")
            # Insert blank lines so column headers land on line 15 (MoTeC CSV standard)
            # 8 metadata lines above + 6 blank = line 15 for headers, line 16 for units
            f.write("\n" * 6)

            print("dropping coolant enable")
            df_copy.drop('Coolant.Fans.Enable',axis=1, inplace=True)
            del units[3]

            # Apply column name mappings: special cases from JSON + dots→spaces for rest
            name_map = _build_column_name_mapping()
            for col in df_copy.columns:
                if col not in name_map:
                    name_map[col] = col.replace('.', ' ')
            df_copy.rename(columns=name_map, inplace=True)

            # Write column headers from the modified copy
            f.write(",".join(f'"{col}"' for col in df_copy.columns) + "\n")
            # Write units row including the 's' unit
            f.write(",".join(f'"{unit}"' for unit in units) + "\n")
            # Write the modified DataFrame as CSV without index and without header
            print(f'output shape {df_copy.shape}')
            df_copy.to_csv(f, index=False, header=False)
        print("Export complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python motec_parser.py <input_ld_file> <output_csv_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        parser = MotecLdParser(input_file)
        parser.parse()
        parser.to_csv(output_file)
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
