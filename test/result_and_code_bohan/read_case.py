from jload import jload

data = jload("test.json")

for d in data:
    try:
        if "axiom" in d["code"] and "lemma" in d["code"]:
            print(d["code"])
            print("\n\n")
            print(d["compilation_result"]["errors"])
            if input() == "1":
                print(d)
    except:
        continue