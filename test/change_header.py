import re
import pandas as pd

def split_proof_at_first_statement(proof):
    """
    Splits the proof string into two parts at the first appearance of 'axiom', 'lemma', or 'theorem'.
    Returns a tuple: (before, after), where 'after' starts with the matched keyword.
    """
    match = re.search(r'\b(axiom|lemma|theorem)\b', proof)
    if match:
        idx = match.start()
        return proof[:idx], proof[idx:]
    else:
        return proof, ''  # No keyword found

txt_file = '/scratch/gpfs/haoyu/Test-time/test/passing_names.txt'

name_set = set()

DEFAULT_HEADER = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat Polynomial Complex\n\n"

with open(txt_file, 'r') as f:
    lines = f.readlines()

    name_set.update(lines)

#print(name_set)

jsonl_file = '/scratch/gpfs/haoyu/Test-time/test/putnam_sampled_4.jsonl'

df = pd.read_json(jsonl_file, lines=True)

for i, r in df.iterrows():
    code = r['lean4_code']
    header, body = split_proof_at_first_statement(code)
    if (r['name']+'\n') in name_set:
        print(r['name'])
        df.iloc[i]['lean4_code'] = DEFAULT_HEADER+body

df.to_json('/scratch/gpfs/haoyu/Test-time/test/putnam_sampled_default_4.jsonl', lines=True, orient='records')