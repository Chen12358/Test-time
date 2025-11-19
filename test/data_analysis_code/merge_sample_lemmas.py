import pandas as pd
import json
import random

# --- 1. Configuration ---

# A. Source of all facts (can be one or more files)
df_json_paths = [
    "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_medium_16_8/merged_results_round_1.json",
    # "/scratch/gpfs/CHIJ/st3812/projects/Test-time/results/Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80_remained_minif2f_split4_64_2/merged_results_round_1.json"
    # Add more paths here
]

# D. How many facts to sample and add to *each* entry
NUM_FACTS_TO_SAMPLE = 30

# # B. The base JSONL file you want to add facts to
# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'

# # C. The new file to save the modified entries
# jsonl_output_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_uniform_sampled.jsonl'

# # B. The base JSONL file you want to add facts to
# jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve.jsonl'

# # C. The new file to save the modified entries
# jsonl_output_path = f'/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading_sampled_{NUM_FACTS_TO_SAMPLE}.jsonl'


# B. The base JSONL file you want to add facts to
jsonl_input_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09.jsonl'

# C. The new file to save the modified entries
jsonl_output_path = f'/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_sampled_{NUM_FACTS_TO_SAMPLE}.jsonl'




# --- 2. Load All Facts into a Single Pool ---
all_dfs = []
print("Loading data from JSON fact files...")
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
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Create the pool by 'summing' (concatenating) all lists in the 'facts' column
    print("Creating facts pool...")
    all_facts_pool = combined_df['facts'].sum()
    
    # De-duplicate the facts to create a uniform sampling pool
    # We assume facts are hashable (e.g., strings)
    try:
        unique_facts_pool = list(set(all_facts_pool))
        print(f"Created a pool of {len(unique_facts_pool)} unique facts (from {len(all_facts_pool)} total facts).")
    except TypeError:
        print("Warning: Facts may not be hashable (e.g., they are dicts). Using non-unique pool.")
        unique_facts_pool = all_facts_pool # Fallback to non-unique list
    
    if not unique_facts_pool:
        print("Fact pool is empty. Cannot sample. Exiting.")
    else:
        # --- 3. Process JSONL File: Read, Sample, Write ---
        print(f"Starting to process {jsonl_input_path}...")
        processed_count = 0
        try:
            # Open both files at the same time
            with open(jsonl_input_path, 'r') as f_in, open(jsonl_output_path, 'w') as f_out:
                for line in f_in:
                    if not line.strip(): # Skip blank lines
                        continue
                        
                    try:
                        entry = json.loads(line)
                        
                        # Ensure 'lemmas' key exists and is a list
                        if "lemmas" not in entry or not isinstance(entry["lemmas"], list):
                            entry["lemmas"] = []
                        
                        # Uniformly sample *with replacement* from the pool
                        # 'random.choices' is robust; it works even if NUM_FACTS_TO_SAMPLE > len(pool)
                        sampled_facts = random.choices(unique_facts_pool, k=NUM_FACTS_TO_SAMPLE)
                        
                        # Add the new sampled facts
                        entry["lemmas"].extend(sampled_facts)
                        
                        # Write the modified entry to the new file
                        f_out.write(json.dumps(entry) + '\n')
                        processed_count += 1
                        
                    except json.JSONDecodeError:
                        print(f"Warning: Skipping a bad JSON line: {line.strip()}")

            print(f"\nDone. Processed and added {NUM_FACTS_TO_SAMPLE} sampled facts to {processed_count} entries.")
            print(f"Successfully saved updated data to {jsonl_output_path}")

        except FileNotFoundError:
            print(f"Error: Input file not found at {jsonl_input_path}")
        except Exception as e:
            print(f"An error occurred during processing: {e}")