# MoTeC .ld Binary Parser

This tool is a Python-based utility designed to decode proprietary MoTeC `.ld` binary telemetry files and convert them into a human-readable CSV format or a pandas DataFrame.

## Overview

The parser reverse-engineers the binary structure of MoTeC M1 series log files, automatically extracting channel names from the header and reading the time-series data from the binary stream.

### Binary Format Specifications (Discovered)

Through binary analysis, the following format specifications were identified:

- **Channel Name Marker**: Channel names are preceded by the byte sequence `\x01\x00\x01\x00\x00\x00`.
- **Channel Discovery**: The tool scans the header for these markers and extracts null-terminated ASCII strings that meet specific criteria (length > 3, printable, starts with a letter).
- **Data Start Offset**: Time-series data begins at byte offset **25,186**.
- **Data Type**: Each sample is a sequence of **16-bit signed integers (`int16`)**.
- **Sample Structure**: One sample consists of $N$ channels, where $N$ is the number of discovered channel names.

## Installation

Ensure you have Python 3.x installed along with the following dependencies:

```bash
pip install numpy pandas
```

## Usage

### Using the CLI Script
The simplest way to convert a file is using the provided `run_parser.py` script:

```bash
python run_parser.py
```
*(Note: You can edit the input/output paths inside `run_parser.py` or modify the script to accept command-line arguments.)*

### Using the Library in Python
You can integrate the `MotecLdParser` class into your own analysis pipeline:

```python
from motec_parser import MotecLdParser

# Initialize the parser
parser = MotecLdParser(r'path/to/your/file.ld')

# Parse the file into a pandas DataFrame
df = parser.parse()

# Export to CSV
parser.to_csv('output_telemetry.csv')

# Access data
print(df.head())
```

## Data Interpretation

**Important**: This tool extracts **raw integer values**. 

MoTeC systems typically store telemetry as integers to save space. To convert these raw values into physical units (e.g., Volts, RPM, kPa), you must apply the appropriate scaling factors (Gain and Offset) using the formula:

$$\text{Physical Value} = (\text{Raw Value} \times \text{Gain}) + \text{Offset}$$

The scaling factors are specific to your vehicle's MoTeC configuration and are not explicitly extracted as a simple table in this version of the tool.

## File Layout
- `motec_parser.py`: The core parsing logic.
- `run_parser.py`: A convenience script for quick conversion.
- `parserReadME.md`: This documentation.
