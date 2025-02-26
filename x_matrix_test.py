import subprocess
import csv
from itertools import product
import sys
import os

# Define the range for dropdown values with a step of 1%
dropdown_1_values = [round(x * 0.05, 2) for x in range(5, 51)]  # From 0.05 to 0.50, step 0.05
dropdown_2_values = [round(x * 0.05, 2) for x in range(5, 51)]  # From 0.05 to 0.50, step 0.05

# Ensure dropdown_2 is always greater than or equal to dropdown_1
combinations = [(d1, d2) for d1, d2 in product(dropdown_1_values, dropdown_2_values) if d1 <= d2]

# File to store results
output_file = 'strategy_results.csv'

total_combinations = len(combinations)

# Function to compare combinations based on ROI, CAGR, and Drawdown
def is_better_combination(new_roi, new_cagr, new_drawdown, best_roi, best_cagr, best_drawdown):
    if new_roi > best_roi:
        return True
    if new_roi == best_roi:
        if new_cagr > best_cagr:
            return True
        if new_cagr == best_cagr:
            return new_drawdown < best_drawdown
    return False

# Check if the results file exists
if os.path.exists(output_file):
    existing_results = {tuple(row[:2]): row for row in csv.reader(open(output_file, 'r')) if row[0] != 'dropdown_1'}
else:
    existing_results = {}

with open(output_file, 'a', newline='') as csvfile:
    fieldnames = ['dropdown_1', 'dropdown_2', 'ROI', 'CAGR', 'Max_Drawdown']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    # Write header only if file is new or empty
    if not existing_results:
        writer.writeheader()

    best_roi = -float('inf')
    best_cagr = -float('inf')
    best_drawdown = float('inf')
    best_combination = (0, 0)

    for i, (dropdown_1, dropdown_2) in enumerate(combinations, 1):
        try:
            # Print progress
            percentage = (i / total_combinations) * 100
            sys.stdout.write(f"\rProcessing: {i}/{total_combinations} ({percentage:.2f}%) - dropdown_1={dropdown_1}, dropdown_2={dropdown_2}")
            sys.stdout.flush()

            # Check if this combination has been calculated before
            if (str(dropdown_1), str(dropdown_2)) in existing_results:
                roi, cagr, drawdown = map(float, existing_results[(str(dropdown_1), str(dropdown_2))][2:])
            else:
                # Run the strategy test script
                result = subprocess.run(['python', 'x.py', '100', '--start_date', '2024-01-01', '--end_date', '2024-12-31', '--skip_simple', '--skip_graf', '--ticker_1', 'QQQ', '--ticker_2', 'QLD', '--ticker_3', 'TQQQ', '--index', 'QQQ', '--dropdown_1', str(dropdown_1), '--dropdown_2', str(dropdown_2)], 
                                        capture_output=True, text=True, check=True)
                
                # Parse the output to find ROI, CAGR, and Drawdown
                output_lines = result.stdout.split('\n')
                roi_line = next((line for line in output_lines if 'ROI:' in line), None)
                cagr_line = next((line for line in output_lines if 'CAGR:' in line), None)
                drawdown_line = next((line for line in output_lines if 'Максимальная просадка:' in line), None)

                if roi_line and cagr_line and drawdown_line:
                    roi = float(roi_line.split()[-1].strip('%'))
                    cagr = float(cagr_line.split()[-1].strip('%'))
                    drawdown = float(drawdown_line.split()[-1].strip('%'))
                    
                    # Write this new result to the CSV
                    writer.writerow({'dropdown_1': dropdown_1, 'dropdown_2': dropdown_2, 'ROI': roi, 'CAGR': cagr, 'Max_Drawdown': drawdown})
                else:
                    raise ValueError("Failed to parse output")

            if is_better_combination(roi, cagr, drawdown, best_roi, best_cagr, best_drawdown):
                best_roi, best_cagr, best_drawdown, best_combination = roi, cagr, drawdown, (dropdown_1, dropdown_2)

        except subprocess.CalledProcessError as e:
            print(f"\nError running script with dropdown_1={dropdown_1}, dropdown_2={dropdown_2}: {e}")
        except ValueError as ve:
            print(f"\nCould not parse ROI, CAGR or Drawdown for dropdown_1={dropdown_1}, dropdown_2={dropdown_2}: {ve}")

    print(f"\nBest ROI: {best_roi:.2f}%, Best CAGR: {best_cagr:.2f}%, Min Max Drawdown: {best_drawdown:.2f}% with dropdown_1={best_combination[0]}, dropdown_2={best_combination[1]}")