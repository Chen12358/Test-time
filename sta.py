from jload import jload

data = jload("mediumweight_batch_results_322.json")

print(len(data))

data = [d for d in data if d['compilation_result']['complete']]

print(len(data))