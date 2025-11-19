from jload import jload, jsave
import re
import argparse


def random_string():
    import random
    import string
    first_char = random.choice(string.ascii_letters)
    chars = string.ascii_letters + string.digits
    rest = ''.join(random.choices(chars, k=11))
    return first_char + rest

def lemma_to_axiom(lemma_code: str) -> str:
    """
    Convert a Lean lemma/theorem code string to its axiom form.
    - Replaces `lemma` or `theorem` with `axiom`
    - Removes the proof part (i.e., everything after `:=`)
    """
    # Remove preceding/trailing whitespace
    code = lemma_code.strip()

    # Replace 'lemma' or 'theorem' at the start of the line with 'axiom'
    code = re.sub(r'^(lemma|theorem)\s+', 'axiom ', code)

    # Remove the proof (anything after ':=')
    if ':=' in code:
        code = code.split(':=', 1)[0].rstrip()

    # If the type ends with ':', remove it.
    code = re.sub(r':\s*$', '', code)

    return code

def normalize_statement(statement: str) -> str:
    """
    Normalize a statement by removing the name part.
    Extracts everything after the lemma/theorem name.
    """
    # Remove 'lemma' or 'theorem' keyword
    statement = re.sub(r'^(lemma|theorem)\s+', '', statement.strip())
    
    # Remove the name (first word) and return the rest
    parts = statement.split(None, 1)
    if len(parts) > 1:
        return parts[1]
    return statement

def main():
    parser = argparse.ArgumentParser(description='Process batch results and convert lemmas to axioms')
    parser.add_argument('--input', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--output', type=str, required=True, help='Output JSON file path')
    parser.add_argument('--incr', action='store_true', help='Incremental update mode')
    
    args = parser.parse_args()
    
    data = jload(args.input)
    data = [d for d in data if not d['compilation_result']['complete']]
    minif2f_path = "/scratch/gpfs/yl7690/projects/DeepSeek-Prover-V1.5/datasets/minif2f_fixed.jsonl"

    minif2f = jload(minif2f_path)

    for d in data:
        d["facts"] = d["facts"] if ("facts" in d and args.incr) else []
        d["lemmas"] = d["lemmas"] if ("lemmas" in d and args.incr) else []

        already_added = set()
        seen_normalized = {}
        
        for stmt in d["lemmas"]:
            normalized_body = normalize_statement(stmt)
            
            temp_stmt = re.sub(r'^(lemma|theorem)\s+', '', stmt.strip())
            name_parts = temp_stmt.split(None, 1)
            
            if name_parts:
                name = name_parts[0]
                already_added.add(name)
                
                if normalized_body not in seen_normalized:
                    seen_normalized[normalized_body] = name
        
        for _pass in d["lemma_collection"]["passes_with_lemmas"]:
            for lemma in _pass["lemmas"]:
                original_name = lemma["name"]
                
                if "sorry" in lemma["statement"]:
                    continue
                
                if "admit" in lemma["statement"]:
                    continue
                
                normalized = normalize_statement(lemma["statement"])
                
                if normalized in seen_normalized:
                    new_name = seen_normalized[normalized]
                else:
                    new_name = random_string()
                    seen_normalized[normalized] = new_name
                
                for l in _pass["lemmas"]:
                    l["statement"] = l["statement"].replace(original_name, new_name)
                
                lemma["name"] = new_name
                
                if lemma["name"] in already_added:
                    continue
                already_added.add(lemma["name"])
                
                axiom = lemma_to_axiom(lemma["statement"])
                d["facts"].append(axiom)
                d["lemmas"].append(lemma["statement"].replace("theorem ", "lemma "))
        
        for m in minif2f:
            if m["problem_id"] == d["name"]:
                d["lean4_code"] = m["lean4_code"]

    jsave(data, args.output)

if __name__ == "__main__":
    main()