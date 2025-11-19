import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging

# --- Basic Configuration ---
logger = logging.getLogger(__name__)

from scheduler.scheduler_service import InferenceSchedulerService, CompilationSchedulerService


async def initial_test(scheduler: InferenceSchedulerService):
    print("SEARCH: Submitting many low-priority initial tasks.")
    # These calls create futures and put tasks on the queue. They will be
    # processed by workers when no higher-priority tasks are available.
    prompt = '''
I would like you to help me prove a problem in Lean 4.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```
axiom MUHuNPWL :
  ∃ (x : ℝ) (y : ℝ) (z : ℝ),
    x ^ (2 : ℕ) + (2 : ℝ) * y ^ (2 : ℕ) + (2 : ℝ) * z ^ (2 : ℕ) + x * y + y * z + z * x = (1 : ℝ) ∧
      x + y + z = √(5 : ℝ) / (2 : ℝ)

axiom SSApccwv (x y z : ℝ) : x ^ (2 : ℕ) + (2 : ℝ) * y ^ (2 : ℕ) + (2 : ℝ) * z ^ (2 : ℕ) + x * y + y * z + z * x = (1 : ℝ) →
    x + y + z ≤ √(5 : ℝ) / (2 : ℝ)

axiom UUQJNhWb :
  ∃ (x : ℝ) (y : ℝ) (z : ℝ),
    x ^ (2 : ℕ) + (2 : ℝ) * y ^ (2 : ℕ) + (2 : ℝ) * z ^ (2 : ℕ) + x * y + y * z + z * x = (1 : ℝ) ∧
      x + y + z = √(5 : ℝ) / (2 : ℝ)

axiom mlmxrTDg :
  ∃ (x : ℝ) (y : ℝ) (z : ℝ),
    x ^ (2 : ℕ) + (2 : ℝ) * y ^ (2 : ℕ) + (2 : ℝ) * z ^ (2 : ℕ) + x * y + y * z + z * x = (1 : ℝ) ∧
      x + y + z = √(5 : ℝ) / (2 : ℝ)
```

Now, complete the following Lean 4 code:

```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat
/-- Let \( x, y, z \) be real numbers such that \( x^2 + 2y^2 + 2z^2 + xy + yz + zx = 1 \). Calculate the maximum value of \( x + y + z \). The answer is \dfrac{\sqrt{5}}{2} --/

theorem OMR_problem_183222 : 
  (∃ x y z : ℝ, x^2 + 2*y^2 + 2*z^2 + x*y + y*z + z*x = 1 ∧ x + y + z = Real.sqrt 5 / 2) ∧
  (∀ x y z : ℝ, x^2 + 2*y^2 + 2*z^2 + x*y + y*z + z*x = 1 → x + y + z ≤ Real.sqrt 5 / 2) := by sorry
```

Recall that besides the problem to prove, a list of proved facts are also given to you as axioms. If they are helpful, integrate them into your proof. You don't need to use all of them, and you don't need to prove them again. If you want to use additional lemmas that are not listed, you should include the lemmas and their proofs in your final proof.

As an example, your final proof should look like this:

```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

axiom xxx (if given as a proved fact)

axiom xxx (if given as a proved fact)

...

lemma xxx := by some proof (if this lemma is not given in list of facts)

lemma xxx := by some proof (if this lemma is not given in list of facts)

...

theorem xxx := by some proof
```

Note that if the lean header used in the problem statement is different (for example, import more libraries), you should switch to that header. Also, you are not allowed to write any axioms not listed before. Any new things you write should be either a lemma or a theorem with the corresponding proof.
Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.
The plan should highlight key ideas, intermediate steps or lemmas, and proof structures that will guide the construction of the final formal proof.

Now please start to prove the problem following the above instructions.
'''


    prompt = '''
I would like you to help me prove a problem in Lean 4.

Before giving you the problem statement, I will first give you several proved facts to you, which may help you to prove the problem. The following proved facts are available to you. These facts are labeled by axiom in Lean 4 and you can directly use them in your proof.
```

```

Now, complete the following Lean 4 code:

```lean4
import Mathlib
import Aesop
 
set_option maxHeartbeats 0
 
open BigOperators Real Nat Topology Rat
 
/-- Show that there are no integers $x$ and $y$ such that $4x^3 - 7y^3 = 2003$.-/
theorem numbertheory_4x3m7y3neq2003 (x y : ℤ) : 4 * x ^ 3 - 7 * y ^ 3 ≠ 2003 := by sorry
```

Recall that besides the problem to prove, a list of proved facts are also given to you as axioms. If they are helpful, integrate them into your proof. You don't need to use all of them, and you don't need to prove them again. If you want to use additional lemmas that are not listed, you should include the lemmas and their proofs in your final proof.

As an example, your final proof should look like this:

```lean4
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

axiom xxx (if given as a proved fact)

axiom xxx (if given as a proved fact)

...

lemma xxx := by some proof (if this lemma is not given in list of facts)

lemma xxx := by some proof (if this lemma is not given in list of facts)

...

theorem xxx := by some proof
```

Note that if the lean header used in the problem statement is different (for example, import more libraries), you should switch to that header. Also, you are not allowed to write any axioms not listed before. Any new things you write should be either a lemma or a theorem with the corresponding proof.
Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.
The plan should highlight key ideas, intermediate steps or lemmas, and proof structures that will guide the construction of the final formal proof.

Now please start to prove the problem following the above instructions.
'''
    # tasks = [
    #     scheduler.inference(
    #         prompt=f"Tell me a joke. Make it funny and long, longer than 5000 words.", 
    #         model="gpt-oss-120b", 
    #         #priority=8,
    #         extra_params={"temperature": 1.0}
    #     ) 
    #     for i in range(300)
    # ]
    tasks = [
        scheduler.inference(
            prompt=prompt, 
            model="Goedel-Prover-V2-8B-reformat_revision_v2", 
            #priority=8,
            extra_params={"temperature": 1.0}
        ) 
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    print("SEARCH: All initial search tasks are complete.")
    for r in results:
        print(r + "\n")

    # tasks = [
    #     lightweight( xxxxx
    #         prompt=f"Tell me a joke", 
    #         model="gpt-oss-120b", 
    #         #priority=8,
    #         extra_params={"temperature": 1.0}
    #     ) 
    #     for i in range(10)
    # ]
    # results = await asyncio.gather(*tasks)
    # print("SEARCH: All initial search tasks are complete.")
    # for r in results:
    #     print(r)

async def initial_test_compiler(scheduler: CompilationSchedulerService):
    print("SEARCH: Submitting many low-priority initial tasks.")
    # These calls create futures and put tasks on the queue. They will be
    # processed by workers when no higher-priority tasks are available.
    name1 = "asd"
    name2 = "psd"
    name3 = "ose"
    name4 = "mathd_algebra_478"
    proof1 = "theorem asd : 0 = 1 := by sorry"
    proof2 = "\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat Polynomial Complex\n\nlemma psd : 0 = 1 := by sorry"
    proof3 = "import Mathlib\n\nlemma pdf : 1 = 1 := by rfl"
    proof4 = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat\n\ntheorem mathd_algebra_478 (b h v : ℝ) (h₀ : 0 < b ∧ 0 < h ∧ 0 < v) (h₁ : v = 1 / 3 * (b * h))\n    (h₂ : b = 30) (h₃ : h = 13 / 2) : v = 65 := by\n  have h₄ : v = (1 / 3 : ℝ) * ((30 : ℝ) * (13 / 2)) := by\n    rw [h₁, h₂, h₃]\n    <;> ring_nf\n    <;> norm_num\n  \n  have h₅ : (1 / 3 : ℝ) * ((30 : ℝ) * (13 / 2)) = 65 := by\n    norm_num\n    <;> ring_nf\n    <;> norm_num\n    <;> linarith\n  \n  have h_main : v = 65 := by\n    rw [h₄, h₅]\n    <;> norm_num\n    <;> linarith\n  \n  exact h_main"
    
    proof5 = '''import Mathlib
import Aesop
set_option maxHeartbeats 0
open BigOperators Real Nat Topology Rat

lemma  cube_mod_seven_cases (x : ℤ) :
    x ^ 3 % 7 = 0 ∨ x ^ 3 % 7 = 1 ∨ x ^ 3 % 7 = 6 := by
  have h : x % 7 = 0 ∨ x % 7 = 1 ∨ x % 7 = 2 ∨ x % 7 = 3 ∨ x % 7 = 4 ∨ x % 7 = 5 ∨ x % 7 = 6 := by
    omega
  rcases h with
    (h | h | h | h | h | h | h) <;>
    (try omega) <;>
    (try {
      simp [h, pow_three, Int.mul_emod, Int.add_emod, Int.sub_emod] <;>
      norm_num <;> omega
    })
lemma four_mul_cube_mod_seven_ne_one (x : ℤ) :
    (4 * x ^ 3) % 7 ≠ 1 := by
  rcases cube_mod_seven_cases x with h | h | h
  · 
    have : (4 * x ^ 3) % 7 = 0 := by
      omega
    omega
  · 
    have : (4 * x ^ 3) % 7 = 4 := by
      omega
    omega
  · 
    have : (4 * x ^ 3) % 7 = 3 := by
      omega
    omega

lemma mod_seven_2003 : (2003 : ℤ) % 7 = 1 := by
  norm_num

  
lemma main_inequality (x y : ℤ) : 4 * x ^ 3 - 7 * y ^ 3 ≠ 2003 := by
  intro h_eq
  have h_mod : (4 * x ^ 3 - 7 * y ^ 3) % 7 = 1 := by
    have : (4 * x ^ 3 - 7 * y ^ 3 : ℤ) = 2003 := h_eq
    simpa [this, mod_seven_2003] using congrArg (fun t => t % 7) this
  have h_mod' : (4 * x ^ 3) % 7 = 1 := by
    
    have : (4 * x ^ 3 - 7 * y ^ 3) % 7 = (4 * x ^ 3) % 7 := by
      have : (7 * y ^ 3 : ℤ) % 7 = 0 := by
        simp [Int.mul_emod, pow_three] <;> norm_num
      simpa [Int.sub_emod, this] using rfl
    simpa [this] using h_mod
  have h_contra : (4 * x ^ 3) % 7 ≠ 1 := four_mul_cube_mod_seven_ne_one x
  exact h_contra h_mod'

theorem numbertheory_4x3m7y3neq2003 (x y : ℤ) : 4 * x ^ 3 - 7 * y ^ 3 ≠ 2003 := by
  exact main_inequality x y'''

    proof6 = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat\n\nlemma   log_pos_of_one_lt {b : ℕ} (hb : 1 < b) : 0 < Real.log (b : ℝ) := by\n  have hℝ : (b : ℝ) > 1 := by norm_cast\n  have : Real.log (b : ℝ) > 0 := Real.log_pos hℝ\n  exact this\n\nlemma log_mul_pos_of_one_lt {a b : ℕ} (ha : 1 < a) (hb : 1 < b) :\n    0 < Real.log ((a : ℝ) * b) := by\n  have h₁ : 0 < Real.log (a : ℝ) :=\n    log_pos_of_one_lt ha\n  have h₂ : 0 < Real.log (b : ℝ) :=\n    log_pos_of_one_lt hb\n  have hsum : Real.log ((a : ℝ) * b) = Real.log (a : ℝ) + Real.log (b : ℝ) := by\n    simpa [Real.log_mul (by positivity) (by positivity)]\n  have : 0 < Real.log ((a : ℝ) * b) := by\n    have : 0 < Real.log (a : ℝ) + Real.log (b : ℝ) := add_pos h₁ h₂\n    simpa [hsum] using this\n  exact this\n\n\nlemma log_w_eq_24_mul_log_x {x w : ℕ}\n    (h0 : Real.log w / Real.log x = 24)\n    (hxpos : 0 < Real.log (x : ℝ)) :\n    Real.log (w : ℝ) = (24 : ℝ) * Real.log (x : ℝ) := by\n  have : Real.log (w : ℝ) = 24 * Real.log (x : ℝ) := by\n    have hne : Real.log (x : ℝ) ≠ 0 := by linarith\n    have : Real.log (w : ℝ) / Real.log (x : ℝ) = (24 : ℝ) := by\n      exact_mod_cast h0\n    field_simp at this\n    simpa using this\n  exact_mod_cast this\n\nlemma log_w_eq_40_mul_log_y {y w : ℕ}\n    (h1 : Real.log w / Real.log y = 40)\n    (hypos : 0 < Real.log (y : ℝ)) :\n    Real.log (w : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := by\n  have hne : Real.log (y : ℝ) ≠ 0 := by linarith\n  have : Real.log (w : ℝ) / Real.log (y : ℝ) = (40 : ℝ) := by\n    exact_mod_cast h1\n  field_simp at this\n  simpa using this\n\nlemma log_w_eq_12_mul_log_xyz {x y z w : ℕ}\n    (h2 : Real.log w / Real.log (x * y * z) = 12)\n    (hposxyz : 0 < Real.log ((x : ℝ) * y * z)) :\n    Real.log (w : ℝ) = (12 : ℝ) * Real.log ((x : ℝ) * y * z) := by\n  have : Real.log (w : ℝ) / Real.log ((x : ℝ) * y * z) = (12 : ℝ) := by\n    exact_mod_cast h2\n  have hne : Real.log ((x : ℝ) * y * z) ≠ 0 := by linarith\n  field_simp at this\n  simpa using this\n\n\nlemma log_x_eq_log_y_add_log_z {x y z : ℕ}\n    (h3 : 24 : ℝ * Real.log (x : ℝ) = 40 : ℝ * Real.log (y : ℝ))\n    (h4 : 24 : ℝ * Real.log (x : ℝ) = 12 : ℝ * (Real.log (x : ℝ) + Real.log (y : ℝ) + Real.log (z : ℝ))) :\n    Real.log (x : ℝ) = Real.log (y : ℝ) + Real.log (z : ℝ) := by\n  have h4' : (2 : ℝ) * Real.log (x : ℝ) =\n      Real.log (x : ℝ) + Real.log (y : ℝ) + Real.log (z : ℝ) := by\n    nlinarith\n  have : Real.log (x : ℝ) = Real.log (y : ℝ) + Real.log (z : ℝ) := by linarith\n  exact this\n\nlemma log_y_eq_three_halves_of_log_z {x y z : ℝ}\n    (hx_eq : Real.log x = Real.log y + Real.log z)\n    (h5 : 3 : ℝ * Real.log (x : ℝ) = 5 : ℝ * Real.log (y : ℝ)) :\n    (2 : ℝ) * Real.log (y : ℝ) = 3 * Real.log (z : ℝ) := by\n  have : 3 * (Real.log (y : ℝ) + Real.log (z : ℝ)) = 5 * Real.log (y : ℝ) := by\n    simpa [hx_eq] using h5\n  linarith\n\nlemma log_w_eq_60_mul_log_z {x y z w : ℕ}\n    (logx_eq : Real.log (x : ℝ) = Real.log (y : ℝ) + Real.log (z : ℝ))\n    (h5 : 3 : ℝ * Real.log (x : ℝ) = 5 : ℝ * Real.log (y : ℝ))\n    (hw_y : Real.log (w : ℝ) = (40 : ℝ) * Real.log (y : ℝ))\n    (hw_x : Real.log (w : ℝ) = (24 : ℝ) * Real.log (x : ℝ))\n    (hw_xyz : Real.log (w : ℝ) = (12 : ℝ) * Real.log ((x : ℝ) * y * z)) :\n    Real.log (w : ℝ) = (60 : ℝ) * Real.log (z : ℝ) := by\n  have h₂ : (40 : ℝ) * Real.log (y : ℝ) = 60 * Real.log (z : ℝ) := by\n    have h₆ : (3 : ℝ) * Real.log (x : ℝ) = (5 : ℝ) * Real.log (y : ℝ) := by\n      simpa using h5\n    have h₇ : Real.log (x : ℝ) = Real.log (y : ℝ) + Real.log (z : ℝ) := logx_eq\n    have h₁₀ : (2 : ℝ) * Real.log (y : ℝ) = 3 * Real.log (z : ℝ) :=\n      log_y_eq_three_halves_of_log_z (by simpa [Real.log_mul (by positivity) (by positivity)])\n        (by simpa [Real.log_mul (by positivity) (by positivity)]) ?_ ?_\n    nlinarith\n  calc\n    Real.log (w : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := hw_y\n    _ = 60 * Real.log (z : ℝ) := h₂\n\ntheorem aime_1983_p1 (x y z w : ℕ) (ht : 1 < x ∧ 1 < y ∧ 1 < z) (hw : 0 ≤ w)\n    (h0 : Real.log w / Real.log x = 24) (h1 : Real.log w / Real.log y = 40)\n    (h2 : Real.log w / Real.log (x * y * z) = 12) : Real.log w / Real.log z = 60 := by\n  \n  rcases ht with ⟨hxgt1, hygt1, hzgt1⟩\n  have hxpos : 0 < Real.log (x : ℝ) := log_pos_of_one_lt hxgt1\n  have hypos : 0 < Real.log (y : ℝ) := log_pos_of_one_lt hygt1\n  have hzpos : 0 < Real.log (z : ℝ) := log_pos_of_one_lt hzgt1\n  have hposxyz : 0 < Real.log ((x : ℝ) * y * z) :=\n    log_mul_pos_of_one_lt hxgt1 hygt1\n\n  \n  have hw_x   := log_w_eq_24_mul_log_x h0 hxpos\n  have hw_y   := log_w_eq_40_mul_log_y h1 hypos\n  have hw_xyz := log_w_eq_12_mul_log_xyz h2 hposxyz\n\n  \n  have h3 : (24 : ℝ) * Real.log (x : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := by\n    have : Real.log (w : ℝ) = (24 : ℝ) * Real.log (x : ℝ) := hw_x\n    have : Real.log (w : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := hw_y\n    linarith\n  have h4 : (24 : ℝ) * Real.log (x : ℝ) = (12 : ℝ) *\n      (Real.log (x : ℝ) + Real.log (y : ℝ) + Real.log (z : ℝ)) := by\n    have : Real.log (w : ℝ) = (24 : ℝ) * Real.log (x : ℝ) := hw_x\n    have : Real.log (w : ℝ) = (12 : ℝ) * Real.log ((x : ℝ) * y * z) := hw_xyz\n    have hmul :\n        Real.log ((x : ℝ) * y * z) =\n          Real.log (x : ℝ) + Real.log (y : ℝ) + Real.log (z : ℝ) := by\n      have h₁ : Real.log ((x : ℝ) * y) =\n          Real.log (x : ℝ) + Real.log (y : ℝ) := by\n        simpa [Real.log_mul (by positivity) (by positivity)]\n      have h₂ : Real.log ((x : ℝ) * y * z) =\n          Real.log ((x : ℝ) * y) + Real.log (z : ℝ) := by\n        simpa [Real.log_mul (by positivity) (by positivity)]\n      simpa [h₁] using h₂\n    linarith\n\n  \n  have h5 : Real.log (x : ℝ) = Real.log (y : ℝ) + Real.log (z : ℝ) :=\n    log_x_eq_log_y_add_log_z (by simpa using h3) (by simpa using h4)\n\n  \n  have h_ratio : (40 : ℝ) * Real.log (y : ℝ) = (60 : ℝ) * Real.log (z : ℝ) := by\n    have : (3 : ℝ) * Real.log (x : ℝ) = (5 : ℝ) * Real.log (y : ℝ) := by\n      have : (24 : ℝ) * Real.log (x : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := by\n        simpa using h3\n      nlinarith\n    have h₈ : (2 : ℝ) * Real.log (y : ℝ) = 3 * Real.log (z : ℝ) :=\n      log_y_eq_three_halves_of_log_z (by simpa [Real.log_mul (by positivity) (by positivity)])\n        (by simpa [Real.log_mul (by positivity) (by positivity)]) ?_ ?_\n    nlinarith\n  have h_w_z : Real.log (w : ℝ) = (60 : ℝ) * Real.log (z : ℝ) := by\n    calc\n      Real.log (w : ℝ) = (40 : ℝ) * Real.log (y : ℝ) := hw_y\n      _ = 60 * Real.log (z : ℝ) := h_ratio\n\n  \n  have h_ne : Real.log (z : ℝ) ≠ 0 := by linarith\n  have : Real.log (w : ℝ) / Real.log (z : ℝ) = (60 : ℝ) := by\n    calc\n      Real.log (w : ℝ) / Real.log (z : ℝ)\n          = ((60 : ℝ) * Real.log (z : ℝ)) / Real.log (z : ℝ) := by\n            simpa [h_w_z]\n      _ = (60 : ℝ) := by\n            field_simp [h_ne]\n  exact_mod_cast this"
    
    # test_list = [(name1, proof1), (name2, proof2), (name3, proof3), (name4, proof4)]

    # test_list = ([("test_problem",proof5)]*10 + [(name1, proof1), (name2, proof2), (name3, proof3), (name4, proof4)] ) * 3 + [("aime_1983_p1", proof6)] * 10
    test_list = [("aime_1983_p1", proof6)] * 1
    tasks = [
        scheduler.compile(
            name=name, 
            code=proof
        ) 
        for name, proof in test_list
    ]
    results = await asyncio.gather(*tasks)
    print("SEARCH: All initial search tasks are complete.")
    for r in results:
        print(r)

async def main():
    # In your main application, you create ONE instance of the scheduler
    # scheduler = InferenceSchedulerService(vllm_gateway_url="http://della-gpu.princeton.edu:8888/", num_workers=20)
    # # scheduler = InferenceSchedulerService(vllm_gateway_url="http://della9.princeton.edu:8888", num_workers=20)
    # scheduler.start()    
    
    # scheduler = CompilationSchedulerService(compilation_gateway_url="http://della-gpu.princeton.edu:9876", num_workers=20)
    # scheduler = CompilationSchedulerService(compilation_gateway_url="http://tiger3.princeton.edu:9876", num_workers=20)
    scheduler = CompilationSchedulerService(compilation_gateway_url="http://localhost:12345", num_workers=20)


    # Different modules can now run concurrently and submit tasks
    # to the same scheduler instance.
    await asyncio.gather(
        initial_test_compiler(scheduler),
    )
    # await asyncio.gather(
    #     initial_test_compiler(scheduler) # This will preempt the initial search tasks
    # )
    scheduler.stop()

if __name__ == '__main__':
    # logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
    #                     datefmt='%m/%d/%Y %H:%M:%S')
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    asyncio.run(main())