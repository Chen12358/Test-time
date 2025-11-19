
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proofsearch.mediumweight.utils import ProofAnalysis


def get_types_num(declarations):
    num_lemmas = 0
    num_axioms = 0
    for k ,v in declarations.items():
        if v['type'] == 'lemma':
            num_lemmas += 1
        elif v['type'] == 'axiom':
            num_axioms += 1
    return num_lemmas, num_axioms




data = []
# Replace 'your_file.jsonl' with the actual path to your file
file_path = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/v2_32B_S80_pass@32_omni.jsonl' 
analysis_file = '/scratch/gpfs/CHIJ/st3812/projects/Test-time/v2_32B_S80_pass@32_use_lemma_analysis.jsonl'

with open(file_path, 'r') as f:
    for line in f:
        # json.loads() parses a JSON string into a Python dict
        data.append(json.loads(line))

# data = data[0:1]

for entry in data:
    code = entry['code']
    compilation_result = entry['compilation_result']
    analysis = ProofAnalysis(code, compilation_result.get('errors'))

    entry.update({"final_analysis_report": analysis.report_json()})


# with open(analysis_file, 'w') as f:
#     for entry in data:
#         f.write(json.dumps(entry) + '\n')

total_lemma_num_success = 0
total_lemma_num_fail = 0
total_inference_num_success = 0
total_inference_num_fail = 0

for entry in data:
    compilation_result = entry['compilation_result']
    num_lemmas, num_axioms = get_types_num(entry["final_analysis_report"]["declarations"])

    if compilation_result.get('complete') == True:

        # total_lemma_num_success += len(entry["final_analysis_report"]["declarations"])
        total_lemma_num_success += num_lemmas
        total_inference_num_success += 1
        

    else:
        # total_lemma_num_fail += len(entry["final_analysis_report"]["declarations"])
        total_lemma_num_fail += num_lemmas
        total_inference_num_fail += 1

print("file analyzed:", file_path)

print(f"Num of success entries: {total_inference_num_success}. \nTotal number of lemmas across success entries: {total_lemma_num_success}")
print(f"Average number of lemmas across success entries: {total_lemma_num_success/total_inference_num_success}")
print(f"Num of fail entries: {total_inference_num_fail}. \nTotal number of lemmas across fail entries: {total_lemma_num_fail}")
print(f"Average number of lemmas across fail entries: {total_lemma_num_fail/total_inference_num_fail}")