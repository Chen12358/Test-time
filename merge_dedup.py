from jload import jload, jsave
import re
import argparse
import numpy as np


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
    Remove the 'lemma/theorem/axiom' keyword and the following name,
    then return the rest of the statement.
    """
    statement = statement.strip()
    # Remove leading axiom/lemma/theorem and the name (first two words)
    return re.sub(r'^(lemma|theorem|axiom)\s+\S+\s*', '', statement, flags=re.DOTALL)

def deduplicate_axioms_by_diversity(axioms, n, model):
    """
    Select n most diverse axioms using embeddings.
    Uses greedy selection based on maximum average distance.
    """
    n = min(n, len(axioms))
    
    if n == 0:
        return []
    
    print(f"Computing embeddings for {len(axioms)} axioms...")
    embeddings = model.encode(["axiom test_lemma " + normalize_statement(i) for i in axioms], show_progress_bar=True, convert_to_numpy=True)
    
    # Normalize embeddings for cosine similarity
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # Greedy selection: pick n most diverse axioms
    selected_indices = []
    remaining_indices = list(range(len(axioms)))
    
    # Start with a random axiom (or the first one)
    first_idx = 0
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    print(f"Selecting {n} most diverse axioms...")
    # Select remaining n-1 axioms
    for _ in range(n - 1):
        if not remaining_indices:
            break
            
        max_min_distance = -1
        best_idx = None
        
        # For each remaining axiom, compute minimum distance to selected axioms
        for idx in remaining_indices:
            # Compute cosine similarity with all selected axioms
            similarities = embeddings[idx] @ embeddings[selected_indices].T
            # Convert to distance (1 - similarity for cosine)
            distances = 1 - similarities
            # Get minimum distance (most similar)
            min_distance = np.min(distances)
            
            # Select the axiom with maximum minimum distance (most different)
            if min_distance > max_min_distance:
                max_min_distance = min_distance
                best_idx = idx
        
        print(max_min_distance)
        print(axioms[best_idx])
        
        if max_min_distance < 0.01:
            break
        
        if best_idx is not None:
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
    
    print(f"Selected {len(selected_indices)} diverse axioms")
    return [axioms[i] for i in selected_indices]

def main():
    parser = argparse.ArgumentParser(description='Process batch results and convert lemmas to axioms')
    parser.add_argument('--input', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--output', type=str, required=True, help='Output JSON file path')
    parser.add_argument('--incr', action='store_true', help='Incremental update mode')
    parser.add_argument('--dedup', action='store_true', help='Enable deduplication by diversity')
    parser.add_argument('--n', type=int, default=10, help='Number of diverse axioms to keep (used with --dedup)')
    
    args = parser.parse_args()
    
    # Load embedding model once if dedup is enabled
    model = None
    if args.dedup:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = "/scratch/gpfs/CHIJ/yong/models/Qwen3-Embedding-8B"
            print(f"Loading embedding model: {model_name}")
            model = SentenceTransformer(model_name, trust_remote_code=True)
        except ImportError:
            print("Warning: sentence-transformers not installed. Deduplication disabled.")
            print("Install with: pip install sentence-transformers")
            args.dedup = False
    
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
        
        # Apply deduplication if requested
        if args.dedup and model is not None:
            print(f"\nDeduplicating {len(d['facts'])} axioms for problem '{d['name']}'...")
            d["facts"] = deduplicate_axioms_by_diversity(d["facts"], args.n, model)
            # Also update lemmas to match
            # d["lemmas"] = d["lemmas"][:args.n]
        
        for m in minif2f:
            if m["problem_id"] == d["name"]:
                d["lean4_code"] = m["lean4_code"]

    print(f"Saving processed data to {args.output}...")
    jsave(data, args.output)

if __name__ == "__main__":
    main()