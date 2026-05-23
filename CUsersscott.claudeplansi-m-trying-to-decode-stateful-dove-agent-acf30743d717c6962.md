# Plan: Extract and Compare Channel Names

## Objective
Extract channel names from a binary `.ld` file using a specific marker and filtering criteria, then compare the result with a reference list in `output.csv`.

## Steps

1. **Parse Reference List**
   - Read `C:\Users\scott\MotecFile\output.csv`.
   - Extract the channel names (column 2) into a list.

2. **Implement Extraction Script**
   - Write a Python script that performs the following:
     - Open `C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld` in binary mode.
     - Search for the marker byte sequence: `\x01\x00\x01\x00\x00\x00`.
     - For each match, extract the following null-terminated string.
     - Apply filters:
       - Minimum length of 3 characters.
       - Must consist only of printable ASCII characters.
       - Must start with a letter.
       - Must not contain specific symbols (`�`, `$`, `<`, `>`, etc.).
     - Store the cleaned names in a list.

3. **Compare and Report**
   - Compare the extracted list with the reference list from `output.csv`.
   - Report the final count of cleaned strings.
   - Report if the lists match exactly in order.
   - If the count is close to 188, print the full extracted list.

## Constraints
- Read-only mode: The Python script must be run via stdin or as a one-liner to avoid creating a `.py` file on disk.
- Use absolute paths for all file accesses.
