
import pandas as pd
import json

# --- 1. Configuration ---
# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve.jsonl'
# jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading.jsonl' # Save to a new file

# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'
# jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading.jsonl' # Save to a new file

# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'
# jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_5times.jsonl' # Save to a new file

jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'
jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_3times.jsonl' # Save to a new file


df = pd.read_json("/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_1.json")
# df = pd.read_json("/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split4_64_2/merged_results_round_1.json")

# --- 2. Load JSONL into a Dictionary for Fast Lookup ---
# We map: problem_id -> entry_dictionary
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

except FileNotFoundError:
    print(f"Error: Input file not found at {jsonl_input_path}")
    # Exit or raise error
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON in {jsonl_input_path}")
    # Exit or raise error


# --- 3. Iterate Through DataFrame and Update the Map ---
update_count = 0
with open(jsonl_output_path, 'w') as f:
    for index, row in df.iterrows():
        problem_name = row["name"]
        facts_to_add = row["facts"] 

        # Check if the df 'name' exists as a 'problem_id' in our map
        if problem_name in jsonl_data_map:
            print(f"Updating problem_id: {problem_name} with {len(facts_to_add)} new lemmas.")
            # Ensure 'lemmas' key exists and is a list
            if "lemmas" not in jsonl_data_map[problem_name] or not isinstance(jsonl_data_map[problem_name]["lemmas"], list):
                jsonl_data_map[problem_name]["lemmas"] = []
            
            # Use extend() to add all items from the 'facts' list
            jsonl_data_map[problem_name]["lemmas"].extend(facts_to_add)
            update_count += 1
            f.write(json.dumps(jsonl_data_map[problem_name]) + '\n')

print(f"Found and updated {update_count} entries.")

# # --- 4. Write the Updated Data Back to a New JSONL File ---
# with open(jsonl_output_path, 'w') as f:
#     for entry in jsonl_data_map.values():
#         f.write(json.dumps(entry) + '\n')

print(f"Successfully saved updated data to {jsonl_output_path}")

