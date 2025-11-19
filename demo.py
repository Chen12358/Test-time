from jload import jload
import random

def convert_to_latex(text):
    # Split the text into blocks based on code blocks
    blocks = []
    current_block = ""
    in_code_block = False
    code_type = ""
    
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for code block start
        if line.startswith('```'):
            if in_code_block:
                # End current code block
                blocks.append((code_type, current_block.rstrip()))
                current_block = ""
                in_code_block = False
                i += 1
                continue
            else:
                # Start new code block
                if current_block:
                    blocks.append(("natural", current_block.rstrip()))
                    current_block = ""
                code_type = line[3:].strip() if line[3:].strip() else "tactics"
                in_code_block = True
                i += 1
                continue
        
        current_block += line + "\n"
        i += 1
        
    # Add final block if exists
    if current_block:
        blocks.append(("natural" if not in_code_block else code_type, current_block.rstrip()))

    # Convert blocks to LaTeX
    latex_output = ""
    for block_type, content in blocks:
        if block_type == "lean4":
            latex_output += "\\begin{answer}\n\\begin{lstlisting}[language=lean,belowskip=-6pt]\n"
            latex_output += content
            latex_output += "\n\\end{lstlisting}\n\\end{answer}\n\n"
        elif block_type == "tactics" or block_type == "lemma":
            latex_output += "\\begin{question}\n\\begin{lstlisting}[language=lean,belowskip=-6pt]\n"
            latex_output += content
            latex_output += "\n\\end{lstlisting}\n\\end{question}\n\n"
        else:  # natural
            latex_output += "\\begin{thought}\n\\begin{lstlisting}[language=prompt,belowskip=-6pt]\n"
            latex_output += content
            latex_output += "\n\\end{lstlisting}\n\\end{thought}\n\n"
            
    return latex_output.strip()

model_ids = [
    "/scratch/gpfs/PLI/yong/DeepSeek-V3-0324",
    "/scratch/gpfs/PLI/yong/DeepSeek-Prover-V2-671B",
    "/scratch/gpfs/PLI/yong/averaged_models_671b/671B-avg-0_50",
    "/scratch/gpfs/PLI/yong/averaged_models_671b/671B-avg-0_30",
]

latex_str = ""

data1 = jload("mediumweight_merged_results_1030.json")
data2 = jload("mediumweight_merged_results_1030_n_4.json")
data3 = jload("mediumweight_merged_results_1030_n_8.json")

_all = {}


for d1 in data1:
    _all[d1["name"]] = {"raw": "\n\n".join(d1["facts"])}

for d1 in data2:
    _all[d1["name"]]["n_4"] = "\n\n".join(d1["facts"])

for d1 in data3:
    _all[d1["name"]]["n_8"] = "\n\n".join(d1["facts"])

for k, v in _all.items():
    latex_str += f"\\section{{{k.replace('_', ' ')}}}\n"
    for _k, _v in v.items():
        latex_str += f"\\subsection{{{_k.replace('_', ' ')}}}\n"
        latex_str += convert_to_latex(_v)

# for d in random.sample(data, 20):
#     latex_str += f"\\section{{{d['name'].replace('_', ' ')}}}\n"
    
#     latex_str += convert_to_latex(d["code"])
#         # print(d[model_id])
#         # print(convert_to_latex(d[model_id]))
#         # input()

with open("train.tex", "w") as f:
    f.write(latex_str)