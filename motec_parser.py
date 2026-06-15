import csv
import io
import json
import numpy as np
import pandas as pd
import os
import struct
import datetime

def decode_string(bytes_val):
    """decode the bytes and remove trailing zeros"""
    try:
        return bytes_val.decode('ascii').replace('\x00', '').strip()
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

    def __init__(self, meta_ptr, data_ptr, event_ptr, event, driver, vehicleid, venue, datetime, short_comment, device_serial="", device_type=""):
        self.meta_ptr, self.data_ptr, self.event_ptr, self.event, self.driver, self.vehicleid, \
        self.venue, self.datetime, self.short_comment = meta_ptr, data_ptr, event_ptr, event, \
                                                       driver, vehicleid, venue, datetime, short_comment
        self.device_serial = device_serial
        self.device_type = device_type

    @classmethod
    def fromfile(cls, f):
        (_, meta_ptr, data_ptr, event_ptr,
            _, _, _,
            device_serial, device_type_raw, _, _, n,
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
        device_type = decode_string(device_type_raw) if isinstance(device_type_raw, bytes) else str(device_type_raw)
        device_serial_str = str(device_serial) if device_serial else ""
        return cls(meta_ptr, data_ptr, event_ptr, event, driver, vehicleid, venue, _datetime, short_comment, device_serial_str, device_type)

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
    def __init__(self, file_path, sample_rate=None, max_rows=None, skip_rows=None):
        self.file_path = file_path
        self.sample_rate = sample_rate  # None = full resolution; integer = target Hz
        self.max_rows = max_rows  # None = all rows; integer = limit output to first N rows
        self.skip_rows = skip_rows  # None = no skip; integer = drop first N rows after downsample
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
        Exports the parsed DataFrame to a CSV file matching the standard MoTeC CSV format:
          Rows 1-12:  Metadata key/value pairs (multi-column quoted format)
          Rows 13-14: BLANK
          Row 15:     Column names (double-quoted, comma-separated)
          Row 16:     Units row (double-quoted, comma-separated)
          Rows 17-18: BLANK
          Row 19+:    Data rows (all values double-quoted)
        """
        if self.df is None or self.head is None:
            raise ValueError("No data parsed. Call parse() first.")

        # Create a copy of the dataframe to avoid modifying the original parser state
        df_copy = self.df.copy()

        # Generate time array: 0.00, 0.01, 0.02... and insert as the first column
        time_array = np.arange(len(df_copy)) * 0.01
        df_copy.insert(0, 'Time', time_array)

        # Extract metadata from .ld header — strip NUL bytes and other control chars
        def clean_metadata(s):
            if not s:
                return ""
            return s.replace('\x00', '').replace('\xff', '')

        driver = clean_metadata(self.head.driver)
        vehicleid = clean_metadata(self.head.vehicleid)
        venue = clean_metadata(self.head.venue)
        session = clean_metadata(self.head.event.session if self.head.event and self.head.event.session else "")
        short_comment = clean_metadata(self.head.short_comment)

        # Device identifier from header — prefer type string (e.g. "M1") over numeric serial
        device_type = clean_metadata(self.head.device_type)
        device_serial = str(self.head.device_serial) if self.head.device_serial else ""
        device_str = device_type if device_type else device_serial

        # Date/time formatting — head.datetime is a Python datetime object
        log_date = self.head.datetime.strftime('%m/%d/%Y') if self.head.datetime else ""
        log_time = self.head.datetime.strftime('%I:%M:%S %p') if self.head.datetime else ""

        # Calculate maximum sample rate and effective output rate
        freqs = [chan.freq for chan in self.channels if chan.freq > 0]
        max_freq = max(freqs) if freqs else 100

        # Downsample if requested — take every Nth row (safe since channels are step-held to max_freq)
        effective_rate = max_freq
        if self.sample_rate is not None and max_freq > self.sample_rate:
            stride = max_freq // self.sample_rate
            df_copy = df_copy.iloc[::stride].reset_index(drop=True)
            # Regenerate Time array at the new sample rate
            time_array = np.arange(len(df_copy)) * (1.0 / self.sample_rate)
            df_copy['Time'] = time_array
            effective_rate = self.sample_rate

        # Skip leading rows if requested — useful for skipping pre-race stationary data
        if self.skip_rows is not None:
            df_copy = df_copy.iloc[self.skip_rows:].reset_index(drop=True)
            # Regenerate Time column so it starts from 0.000 after skip
            time_array = np.arange(len(df_copy)) * (1.0 / effective_rate)
            df_copy['Time'] = time_array

        # Truncate to max_rows if requested — for debugging/testing large files
        if self.max_rows is not None:
            df_copy = df_copy.head(self.max_rows).reset_index(drop=True)
            # Regenerate Time column so it's contiguous from 0.000 after truncation
            time_array = np.arange(len(df_copy)) * (1.0 / effective_rate)
            df_copy['Time'] = time_array

        # Re-coerce all columns to numeric after any truncation/modification — fills NaN with 0
        for col in df_copy.columns:
            if col not in ('GPS Latitude', 'GPS Longitude'):
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)

        # Mark invalid GPS coordinates as NaN — raw zeros in the .ld file mean
        # "no GPS lock". Don't fill these with 0 because they plot thousands of meters off-track.
        for gps_col, valid_range in [('GPS Latitude', (35.0, 50.0)),
                                     ('GPS Longitude', (-125.0, -65.0))]:
            if gps_col in df_copy.columns:
                vals = pd.to_numeric(df_copy[gps_col], errors='coerce')
                # Values outside continental US range are invalid GPS (zeros, etc.)
                invalid_mask = vals.isna() | (vals < valid_range[0]) | (vals > valid_range[1])
                df_copy.loc[invalid_mask, gps_col] = np.nan

        duration_s = len(df_copy) / effective_rate

        # Get units for all channels discovered, matching the DataFrame columns
        units = []
        seen_names = {}
        for chan in self.channels:
            name = chan.name
            if name in seen_names:
                seen_names[name] += 1
            else:
                seen_names[name] = 0
            units.append(chan.unit)

        # Add 's' as the first element of the units row for the Time column
        units.insert(0, 's')

        # Apply column name mappings: special cases from JSON + dots→spaces for rest
        name_map = _build_column_name_mapping()
        for col in df_copy.columns:
            if col not in name_map:
                name_map[col] = col.replace('.', ' ')
        df_copy.rename(columns=name_map, inplace=True)

        # Synthesize "Lap State" column if missing — raceAgent requires it for lap detection
        # Lap State: 0=unknown, 1=idle/pit, 2=rolling/pre-lap, 3=racing
        if 'Lap State' not in df_copy.columns:
            lap_state = np.ones(len(df_copy), dtype=int)  # default: idle
            has_gps_speed = 'GPS Speed' in df_copy.columns
            has_lap_number = 'Lap Number' in df_copy.columns

            if has_gps_speed and has_lap_number:
                # Use Lap Number as ground truth to group racing data.
                # Threshold must be high enough to exclude warmup/pit-entrance fragments.
                gps_speed = pd.to_numeric(df_copy['GPS Speed'], errors='coerce').fillna(0)
                lap_number = pd.to_numeric(df_copy['Lap Number'], errors='coerce').fillna(0)

                # Identify on-track rows: speed > 40 km/h excludes slow warmup and pit movement.
                # Real racing laps at Lime Rock maintain speeds well above this even in corners.
                on_track_mask = gps_speed > 40

                # For each unique Lap Number, group all on-track rows together.
                # Filter out tiny groups (< 15 seconds) to avoid fragmented pit-stint data.
                min_lap_rows = max(10, int(15 * effective_rate))

                for lap_val in lap_number[on_track_mask].unique():
                    if lap_val <= 0:
                        continue  # skip pre-race idle laps
                    lap_rows = (lap_number == lap_val) & on_track_mask
                    if lap_rows.sum() >= min_lap_rows:
                        lap_state[lap_rows] = 3

                # Set rolling/pre-lap for moderate-speed rows that weren't classified as racing
                rolling_mask = (gps_speed >= 1) & (gps_speed <= 40) & (lap_state == 1)
                lap_state[rolling_mask] = 2
                # Mark GPS-invalid rows
                lap_state[gps_speed < 0] = 0

            elif has_gps_speed:
                # Fallback without Lap Number — simple threshold, smoothed with median filter
                gps_speed = pd.to_numeric(df_copy['GPS Speed'], errors='coerce').fillna(0)
                lap_state[gps_speed > 15] = 3
                lap_state[(gps_speed >= 1) & (gps_speed <= 15)] = 2
                lap_state[gps_speed < 0] = 0

            # Insert Lap State after Time column (index 1)
            time_idx = list(df_copy.columns).index('Time') if 'Time' in df_copy.columns else 0
            df_copy.insert(time_idx + 1, 'Lap State', lap_state)
            # Add corresponding unit entry — units[0] is 's' for Time, Lap State goes at index 1
            units.insert(1, '')

        # Re-coerce all columns to numeric after any truncation/modification — fills NaN with 0
        for col in df_copy.columns:
            if col not in ('GPS Latitude', 'GPS Longitude'):
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)

        # Apply precision formatting: GPS lat/lon get 6 decimal places, Time gets 3 (ms precision for unique timestamps), rest get 1
        gps_cols = {'GPS Latitude', 'GPS Longitude'}
        for col in df_copy.columns:
            if col in gps_cols:
                # Invalid GPS coords are NaN — write empty string so track plot skips them
                df_copy[col] = df_copy[col].map(lambda x: '' if pd.isna(x) else f'{float(x):.6f}')
            elif col == 'Time':
                df_copy[col] = df_copy[col].map(lambda x: f'{float(x):.3f}')
            else:
                df_copy[col] = df_copy[col].map(lambda x: f'{float(x):.1f}')

        # Write the CSV file with exact MoTeC row positioning
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            # --- Rows 1-12: Standard MoTeC multi-column quoted metadata ---
            f.write(f'"Format","MoTeC CSV File",,,"Workbook",""\n')
            f.write(f'"Venue","{venue}",,,"Worksheet",""\n')
            f.write(f'"Vehicle","{vehicleid}",,,"Vehicle Desc",""\n')
            f.write(f'"Driver","{driver}",,,"Engine ID",""\n')
            f.write(f'"Device","{device_str}"\n')
            f.write(f'"Comment","{short_comment}",,,"Session","{session}"\n')
            f.write(f'"Log Date","{log_date}",,,"Origin Time","0.000","s"\n')
            f.write(f'"Log Time","{log_time}",,,"Start Time","0.000","s"\n')
            f.write(f'"Sample Rate","{effective_rate:.3f}","Hz",,"End Time","{duration_s:.3f}","s"\n')
            f.write(f'"Duration","{duration_s:.3f}","s",,"Start Distance","0","ft"\n')
            f.write(f'"Range","entire outing",,,"End Distance","",""\n')
            f.write(f'"Beacon Markers","""\n')

            # --- Rows 13-14: BLANK ---
            f.write("\n\n")

            # --- Row 15: Column names (double-quoted) ---
            f.write(",".join(f'"{col}"' for col in df_copy.columns) + "\n")

            # --- Row 16: Units row (double-quoted) ---
            f.write(",".join(f'"{unit}"' for unit in units) + "\n")

            # --- Rows 17-18: BLANK ---
            f.write("\n\n")

            # --- Row 19+: Data rows (all values double-quoted to match Motec export) ---
            buf = io.StringIO()
            df_copy.to_csv(buf, index=False, header=False, quoting=csv.QUOTE_ALL)
            f.write(buf.getvalue())

if __name__ == "__main__":
    import argparse, sys

    ap = argparse.ArgumentParser(description='Convert Motec .ld binary files to standard MoTeC CSV format.')
    ap.add_argument('input', help='Path to input .ld file')
    ap.add_argument('output', help='Path to output .csv file')
    ap.add_argument('--sample-rate', type=int, default=None,
                    help='Target output sample rate in Hz (default: full resolution). '
                         'Lower values reduce file size by taking every Nth row.')
    ap.add_argument('--max-rows', type=int, default=None,
                    help='Limit output CSV to first N data rows (default: all rows). '
                         'Useful for debugging/testing with large files.')
    ap.add_argument('--skip-rows', type=int, default=None,
                    help='Skip first N data rows (after downsample). '
                         'Useful for skipping pre-race stationary data. '
                         'For the limeRock file at 10 Hz, skip ~6440 to start at racing laps.')
    args = ap.parse_args()

    try:
        parser = MotecLdParser(args.input, sample_rate=args.sample_rate, max_rows=args.max_rows, skip_rows=args.skip_rows)
        parser.parse()
        if args.sample_rate:
            print(f"Downsampling to {args.sample_rate} Hz...")
        if args.skip_rows:
            print(f"Skipping first {args.skip_rows} rows...")
        if args.max_rows:
            print(f"Limiting output to first {args.max_rows} rows...")
        parser.to_csv(args.output)
        print(f"Successfully converted {args.input} to {args.output}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
