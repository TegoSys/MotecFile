# MoTeC .ld Binary Parser

Converts Motec `.ld` binary log files to standard MoTeC CSV format for import into the raceAgent backend at `C:\Users\scott\raceGit\raceAgent`.

## Quick Start

```powershell
# Full resolution (preserves all samples)
python motec_parser.py "C:\path\to\file.ld" "output.csv"

# Downsampled to 10 Hz (~1/10th the rows, ~250 MB for a typical 3-hour race)
python motec_parser.py "C:\path\to\file.ld" "output.csv" --sample-rate 10
```

## Architecture

### Binary Format — `.ld` File Layout

The Motec `.ld` format is pointer-based, not fixed-offset:

| Section | Location | Notes |
|---------|----------|-------|
| **File Header** (`ldHead`) | Offset 0, ~1762 bytes | Contains pointers to channel metadata & event data |
| **Event Chain** (`ldEvent` → `ldVenue` → `ldVehicle`) | Arbitrary offset via pointer | Nested: event points to venue which optionally points to vehicle |
| **Channel Metadata** (`ldChan`, linked list) | Arbitrary offset via pointer | Doubly-linked list, 116 bytes per entry |
| **Channel Data Blocks** | Scattered at arbitrary offsets | Each `ldChan` has its own `data_ptr` and `data_len` |

See `motecFileSpec.txt` for full struct layout details.

### Parsing Pipeline

1. **`read_ldfile()`** reads the file header, then walks the channel metadata linked list.
2. **`MotecLdParser.parse()`** extracts scaled data for each channel:
   - Determines max frequency across all channels (usually 100 Hz).
   - Step-holds lower-frequency channels by repeating each sample `max_freq // chan.freq` times (e.g., a 10 Hz channel is repeated 10× per sample).
   - Trims or pads to `max_data_len`.
   - All columns coerced to numeric; NaN → 0.
3. **`to_csv()`** exports with standard MoTeC CSV header format:

| Row(s) | Content |
|--------|---------|
| 1–12 | Metadata key/value pairs (multi-column quoted format) |
| 13–14 | BLANK |
| 15 | Column names (double-quoted) |
| 16 | Units row (double-quoted) |
| 17–18 | BLANK |
| 19+ | Data rows (all values double-quoted via `csv.QUOTE_ALL`) |

This structure is required by the raceAgent backend parser in `processor.py` (`_parse_motec_header()`, `start_row = 18`).

### Downsampling

When `--sample-rate N` is specified, the parser takes every `max_freq // N` rows after all channels are step-held to max frequency. Time column is regenerated at `1/N` second intervals. This reduces a typical 3-hour race from ~2.5 GB (100 Hz) to ~250 MB (10 Hz).

## Key Files

| File | Purpose |
|------|---------|
| `motec_parser.py` | Main parser — binary reader + CSV writer |
| `columnMap.json` | 63 entries mapping truncated channel names → full names |
| `run_parser.py` | Convenience wrapper with hardcoded paths |
| `ldparser.py` | Older implementation with read/write support |
| `motecFileSpec.txt` | Reverse-engineered binary format specification |
| `motecExportFormat.txt` | Reference MoTeC CSV header (12-row example) |

## Channel Data Types

Resolution based on `(dtype_a, dtype)` from channel metadata:

| `dtype_a` | `dtype` → numpy type |
|-----------|---------------------|
| `0x07` | 2→float16, 4→float32 |
| `0`, `0x03`, `0x05` | 2→int16, 4→int32 |
| `0x08` + dtype=8 | float64 |
| Other (e.g., `0x06`) | **Not mapped** → channel is NaN-filled → coerced to 0 |

### Scaling Formula

Raw values are scaled per-channel: `(raw / scale × 10^(-dec_places) + shift) × mul`

Most channels use identity scaling (shift=0, mul=1, scale=1, dec=0). A few diagnostic or engine-load channels have non-trivial values.

## Column Naming

Channel names in the binary use dots (`Coolant.Temperature`). These are mapped to space-separated names (`Coolant Temperature`) via:
1. `columnMap.json` — 63 special-case entries for truncated names
2. Fallback: replace `.` with space

## Metadata Mapping

The `.ld` header provides these fields, mapped to standard MoTeC CSV metadata rows:

| `.ld` Field | → CSV Row Key | Notes |
|-------------|--------------|-------|
| `driver` | `Driver` | |
| `vehicleid` | `Vehicle` | |
| `venue` | `Venue` | |
| `event.session` | `Session` | |
| `short_comment` | `Comment` | |
| `date` (DD/MM/YYYY) | `Log Date` (MM/DD/YYYY) | Re-formatted for US locale |
| `time` (24h) | `Log Time` (12h AM/PM) | Re-formatted |
| `device_type` | `Device` | Falls back to `device_serial` if empty |
| N/A | `Duration`, `End Time` | Computed from row count ÷ sample rate |

Fields not available in the binary (Beacon Markers, Engine ID, Start/End Distance) are written as empty quoted strings.

## Lessons Learned

- **Never drop columns unconditionally** — The original code dropped `Coolant.Fans.Enable` by name and assumed it was always at index 3. Files without that channel crashed with KeyError, and the `del units[3]` corrupted the units array for files where the channel order differed.
- **Step-hold is essential for multi-rate channels** — A typical file has channels at 1, 10, 20, 50, and 100 Hz. Without expanding lower-frequency channels, pandas left-aligns and NaN-pads the gap. Expansion by `max_freq // chan.freq` produces aligned data.
- **Quoted values matter** — The raceAgent backend `_parse_motec_header()` uses `line.split(',', 1)` to extract metadata key/value pairs. Unquoted values with commas break parsing. Always use `csv.QUOTE_ALL` for data rows and double-quote all metadata values.
- **Blank rows are structural** — The backend hardcodes `start_row = 18`. Deviating from the MoTeC blank-row convention (rows 13-14, 17-18) shifts the data offset and causes parse errors.
- **Non-ASCII bytes in `.ld` comment/vehicle blocks** — Some channels have non-ASCII bytes where string fields are expected. `decode_string()` gracefully falls back to empty string on decode errors — don't remove this defensive pattern.

## Backend Integration Plan (future)

The raceAgent backend will eventually call this parser programmatically rather than via CLI. The integration points:
- Instantiate `MotecLdParser(input_path, sample_rate=10)` and call `.parse()` then `.to_csv(output_path)`.
- The output CSV is already compatible with `processor.py`'s `_parse_motec_header()` — no backend changes needed.
- For a conversion service: accept uploaded `.ld` files, run parser with configurable sample rate, store result in `backend/data/raw_files/`, then trigger the existing processing pipeline.
