import argparse
import os
import json
import random
import string

import pandas as pd
import numpy as np

def random_string(length=8):
    letters = string.ascii_letters  # 只包含A-Z和a-z
    return ''.join(random.choices(letters, k=length))

def substitue_lemma_name(lemma_str, new_name, new_name_prefix='axiom '):
    # substitute the lemma name in the lemma string with new_name
    # the string starts from 'lemma', 'theorem', or 'axiom', then a space, then the lemma name. then there is a space or a :
    lemma_str = lemma_str.strip()
    if lemma_str.startswith('lemma '):
        prefix = 'lemma '
        lemma_str = lemma_str[6:]
    elif lemma_str.startswith('theorem '):
        prefix = 'theorem '
        lemma_str = lemma_str[8:]
    elif lemma_str.startswith('axiom '):
        prefix = 'axiom '
        lemma_str = lemma_str[6:]
    else:
        return lemma_str

    # remove the first part until the first space or colon
    if ' ' in lemma_str:
        rest = lemma_str.split(' ', 1)[1]
    elif ':' in lemma_str:
        rest = lemma_str.split(':', 1)[1]
    else:
        rest = ''
    new_str = new_name_prefix + new_name + ' ' + rest
    # if axiom, omit proof
    if 'axiom' in new_name_prefix:
        new_str = (new_str.split(':= by')[0]).strip()
    elif 'lemma' in new_name_prefix or 'theorem' in new_name_prefix:
        # if lemma or theorem, substitute the proof part to sorry
        new_str = (new_str.split(':= by')[0]).strip()
        new_str += ' := by sorry'  # add a sorry proof
    return new_str

input_file = '/scratch/gpfs/haoyu/Test-time/test/omni_scaffolded_lemmas.jsonl'

df = pd.read_json(input_file, lines=True)
lemmas_list = []
for _, r in df.iterrows():
    lemma_without_process = r['lemma']
    lemma_after_process = [substitue_lemma_name(lemma, random_string()) for lemma in lemma_without_process]
    lemmas_list.append(lemma_after_process)

df['lemmas'] = lemmas_list

df.to_json(input_file, lines=True, orient='records')