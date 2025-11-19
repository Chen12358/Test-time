import pandas as pd
import json

# --- 1. Configuration ---
# List of all JSON files you want to read into DataFrames
df_json_paths = [
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_1.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_2.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_3.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_4.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_5.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_6.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_7.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_8.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split1_64_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split2_64_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split3_64_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split4_64_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-32B-reformat_revision_v2_S80-merge80_remained_minif2f_split1_16_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-32B-reformat_revision_v2_S80-merge80_remained_minif2f_split2_16_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-32B-reformat_revision_v2_S80-merge80_remained_minif2f_split3_16_2/merged_results_round_1.json",
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-32B-reformat_revision_v2_S80-merge80_remained_minif2f_split4_16_2/merged_results_round_1.json",
    # Add more paths here as needed
    # "/path/to/your/other/results.json"
]

# # JSONL input and output paths (same as your script)
# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'
# jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_COMBINED.jsonl' # New output file name

# JSONL input and output paths (same as your script)
jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve.jsonl'
jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_COMBINED.jsonl' # New output file name


# --- 2. Load and Combine All DataFrames ---
all_dfs = []
print("Loading data from JSON files...")
for path in df_json_paths:
    try:
        df = pd.read_json(path)
        all_dfs.append(df)
        print(f"  Successfully loaded {len(df)} rows from {path}")
    except Exception as e:
        print(f"Error loading {path}: {e}")

if not all_dfs:
    print("No DataFrames were loaded. Exiting.")
else:
    # Concatenate all dataframes into one
    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"Total rows combined: {len(combined_df)}")

    # Group by 'name' and 'sum' the 'facts' (which concatenates the lists)
    print("Grouping facts by problem name...")
    # .sum() on list columns concatenates them
    grouped_facts = combined_df.groupby('name')['facts'].sum() 
    print(f"Found {len(grouped_facts)} unique problem names with facts.")


    # --- 3. Load JSONL into a Dictionary for Fast Lookup ---
    # (This section is identical to your original script)
    jsonl_data_map = {}
    try:
        with open(jsonl_input_path, 'r') as f:
            for line in f:
                if line.strip(): # Avoid blank lines
                    entry = json.loads(line)
                    if "problem_id" in entry:
                        jsonl_data_map[entry["problem_id"]] = entry
                    else:
                        print(f"Warning: Line missing 'problem_id': {line.strip()}")
        print(f"Loaded {len(jsonl_data_map)} entries from {jsonl_input_path}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {jsonl_input_path}")
        # Exit or raise error
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON in {jsonl_input_path}")
        # Exit or raise error


    # --- 4. Iterate Through Grouped Data and Update/Write ---
    # We now iterate over the 'grouped_facts' Series instead of the original 'df'
    update_count = 0
    with open(jsonl_output_path, 'w') as f:
        # .items() gives (index, value) which is (problem_name, facts_to_add)
        for problem_name, facts_to_add in grouped_facts.items():
            
            # Check if the grouped 'name' exists as a 'problem_id' in our map
            if problem_name in jsonl_data_map:
                print(f"Updating problem_id: {problem_name} with {len(facts_to_add)} combined new lemmas.")
                
                # Ensure 'lemmas' key exists and is a list
                if "lemmas" not in jsonl_data_map[problem_name] or not isinstance(jsonl_data_map[problem_name]["lemmas"], list):
                    jsonl_data_map[problem_name]["lemmas"] = []
                
                # Use extend() to add all items from the combined 'facts_to_add' list
                jsonl_data_map[problem_name]["lemmas"].extend(facts_to_add)
                update_count += 1
                
                # Write the updated entry to the new file
                # This maintains your original script's logic of only writing updated files
                f.write(json.dumps(jsonl_data_map[problem_name]) + '\n')

    print(f"Found, updated, and wrote {update_count} entries.")
    print(f"Successfully saved updated data to {jsonl_output_path}")