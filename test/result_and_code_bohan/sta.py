from jload import jload, jsave

data = jload("mediumweight_batch_results_32.json")

a = 0
for d in data:
    if d["compilation_result"]["complete"] and  d["compilation_result"]["pass"] and "admit" not in d["code"]:
        print(d["code"])
        # input()
        a += 1

print(a)