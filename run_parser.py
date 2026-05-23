from motec_parser import MotecLdParser
import os

def main():
    input_file = r'C:\Users\scott\Downloads\S1_#25606_20260426_191239_02.ld'
    output_file = r'C:\Users\scott\MotecFile\decoded_telemetry.csv'

    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return

    print(f"Starting MoTeC .ld conversion: {input_file}")

    try:
        parser = MotecLdParser(input_file)
        df = parser.parse()

        print("\n--- DataFrame Summary ---")
        print(f"Shape: {df.shape}")

        cols_to_show = [col for col in ['Brake.State', 'Engine.Speed.Reference.Engine Sprpm', 'ECU.Battery.Voltage'] if col in df.columns]

        if cols_to_show:
            print("\nFirst 5 rows:")
            print(df[cols_to_show].head())
            if len(df) > 1000:
                print("\nMiddle 5 rows (sample 36000):")
                print(df[cols_to_show].iloc[36000:36005])
            print("\nLast 5 rows:")
            print(df[cols_to_show].tail())
        else:
            print("\nFirst 5 rows of first 5 columns:")
            print(df.iloc[:5, :5])

        parser.to_csv(output_file)
        print(f"\nSuccess! File saved to {output_file}")

    except Exception as e:
        print(f"An error occurred during parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
