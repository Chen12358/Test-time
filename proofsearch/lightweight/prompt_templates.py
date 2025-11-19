INFERENCE_NOFACTS_TEMPLATE = """
Complete the following Lean 4 code:

```lean4
{original_question_lean4}
```

Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.
The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof.
"""

INFERENCE_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE = """
I would like you to help me prove a problem in Lean 4.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```
```

Now, complete the following Lean 4 code:

```lean4
{original_question_lean4}
```

Recall that besides the problem to prove, a list of proved facts are also given to you as axioms. If they are helpful, integrate them into your proof. You don't need to use all of them, and you don't need to prove them again. If you want to use additional lemmas that are not listed, you should include the lemmas and their proofs in your final proof.

As an example, your final proof should look like this:

```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

lemma xxx := by some proof (if this lemma is not given in list of facts)

lemma xxx := by some proof (if this lemma is not given in list of facts)

...

theorem xxx := by some proof
```

Note that if the lean header used in the problem statement is different (for example, import more libraries), you should switch to that header. Also, you are not allowed to write any axioms not listed before. Any new things you write should be either a lemma or a theorem with the corresponding proof.
Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.
The plan should highlight key ideas, intermediate steps or lemmas, and proof structures that will guide the construction of the final formal proof.

Now please start to prove the problem following the above instructions.
"""

INFERENCE_AXIOMS_LEMMA_OUTPUT_TEMPLATE = """
I would like you to help me prove a problem in Lean 4.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```
{axioms}
```

Now, complete the following Lean 4 code:

```lean4
{original_question_lean4}
```

Recall that besides the problem to prove, a list of proved facts are also given to you as axioms. If they are helpful, integrate them into your proof. You don't need to use all of them, and you don't need to prove them again. If you want to use additional lemmas that are not listed, you should include the lemmas and their proofs in your final proof.

As an example, your final proof should look like this:

```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

lemma xxx := by some proof (if this lemma is not given in list of facts)

lemma xxx := by some proof (if this lemma is not given in list of facts)

...

theorem xxx := by some proof
```

Note that if the lean header used in the problem statement is different (for example, import more libraries), you should switch to that header. Also, you are not allowed to write any axioms not listed before. Any new things you write should be either a lemma or a theorem with the corresponding proof.
Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.
The plan should highlight key ideas, intermediate steps or lemmas, and proof structures that will guide the construction of the final formal proof.

Now please start to prove the problem following the above instructions.
"""

###########################################################
# Prompt template for revision
###########################################################

REVISION_NOFACTS_TEMPLATE = "Complete the following Lean 4 code:\n\n```lean4\n{original_question_lean4}```\n\nFollowing is a proof with flaws, and its corresponding compilation error feedback from the compiler. You can refer to it and give your answer. Incorrect proof:\n\n```lean4\n{last_full_proof}\n```\n\nError message: (we use <error></error> to signal the position of the error)\n\"\"\"\n{error_message_for_prev_round}\n\"\"\"\nBefore producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\nThe plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof."

REVISION_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE = """
I would like you to help me revise a proof in lean 4. I will first give you the problem, the proof with flaws, and the corresponding error message.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```
```

The goal is to prove the following problem in lean 4:

```lean4
{original_question_lean4}
```

Following is a proof of the previous problem, possibly using the given proved facts.

```lean4
{last_full_proof}
```

Now I would like you to give me a detailed walk-through on the revision of the previous Lean 4 proof. I compiled the provided proof using Lean 4 verifier, and I get the following error messages. Error message: (we use <error></error> to signal the position of the error)

\"\"\"
{error_message_for_prev_round}
\"\"\"

Now, please help me to revise the Lean 4 code based on the error messages. Before producing the revised Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies. The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof. Most importantly, because the goal is to revise the Lean 4 code instead of generating a completely new one, the plan should contain a comment block on if the genenral proof strategy is correct (by comparing with the key ideas, intermediate lemmas, etc), and a detailed walk-thorough how to revise the Lean 4 code to fix the error messages. For example, you should explain what's your thought on a specific error, and how to revise the code the fix the error. However, if you feel like the original proof is totally wrong, you can generate a new one.

Note that when generating the revised proof, you are encouraged to use the proved facts (listed as axioms) since they are likely to be related to the problem, and they might give you some thoughts about the proof strategy even if you do not directly use them. Besides, you are also encouraged to follow the previous proof structure, i.e., if there is a lemma in the previous proof with flaw, you are also encouraged to keep that lemma (if that lemma is proved without error message) or just modify the lemma in place (if that lemma is not proved and there are corresponding error messages). Note that when writing the proof, please do not write any new axioms besides the given proved facts. Please put the revised proof in the last ```lean4\n(your revised proof)\n``` block.
"""

REVISION_AXIOMS_LEMMA_OUTPUT_TEMPLATE = """
I would like you to help me revise a proof in lean 4. I will first give you the problem, the proof with flaws, and the corresponding error message.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```
{axioms}
```

The goal is to prove the following problem in lean 4:

```lean4
{original_question_lean4}
```

Following is a proof of the previous problem, possibly using the given proved facts.

```lean4
{last_full_proof}
```

Now I would like you to give me a detailed walk-through on the revision of the previous Lean 4 proof. I compiled the provided proof using Lean 4 verifier, and I get the following error messages. Error message: (we use <error></error> to signal the position of the error)

\"\"\"
{error_message_for_prev_round}
\"\"\"

Now, please help me to revise the Lean 4 code based on the error messages. Before producing the revised Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies. The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof. Most importantly, because the goal is to revise the Lean 4 code instead of generating a completely new one, the plan should contain a comment block on if the genenral proof strategy is correct (by comparing with the key ideas, intermediate lemmas, etc), and a detailed walk-thorough how to revise the Lean 4 code to fix the error messages. For example, you should explain what's your thought on a specific error, and how to revise the code the fix the error. However, if you feel like the original proof is totally wrong, you can generate a new one.

Note that when generating the revised proof, you are encouraged to use the proved facts (listed as axioms) since they are likely to be related to the problem, and they might give you some thoughts about the proof strategy even if you do not directly use them. Besides, you are also encouraged to follow the previous proof structure, i.e., if there is a lemma in the previous proof with flaw, you are also encouraged to keep that lemma (if that lemma is proved without error message) or just modify the lemma in place (if that lemma is not proved and there are corresponding error messages). Note that when writing the proof, please do not write any new axioms besides the given proved facts. Please put the revised proof in the last ```lean4\n(your revised proof)\n``` block.
"""