import pandas as pd

def add_sequential_no_column(input_csv_path, output_csv_path):
    """
    Adds a 'no' column with sequential numbers to a CSV file.

    Args:
        input_csv_path (str): The path to the input CSV file.
        output_csv_path (str): The path where the new CSV file with the 'no' column will be saved.
    """
    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(input_csv_path)

        # Add the 'no' column with sequential numbers starting from 1
        # The index is 0-based, so we add 1 to get 1-based numbering.
        df.insert(0, 'no', range(1, 1 + len(df)))

        # Save the modified DataFrame to a new CSV file
        df.to_csv(output_csv_path, index=False)

        print(f"Successfully added 'no' column to '{input_csv_path}' and saved to '{output_csv_path}'")

    except FileNotFoundError:
        print(f"Error: The file '{input_csv_path}' was not found. Please check the path.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # --- Configuration ---
    # Replace 'your_input.csv' with the actual name of your CSV file
    input_csv_file = 'paper_result.csv'
    # Replace 'your_output.csv' with the desired name for the output file
    output_csv_file = 'paper_result_no.csv'
    # -------------------

    add_sequential_no_column(input_csv_file, output_csv_file)