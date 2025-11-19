# test_lightweight_live.py

import asyncio
import logging
from pprint import pprint

import pandas as pd
import os
import argparse

# --- Import the REAL services and the function to test ---
from scheduler.scheduler_service import InferenceSchedulerService, P_INITIAL, P_REVISION
from scheduler.scheduler_service import CompilationSchedulerService
from proofsearch.lightweight.lightweightsearch import lightweight_inference

# --- Configuration ---
# Set up basic logging to see the output from all components
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



# The URLs for your running services
LLM_GATEWAY_URL = "http://della-gpu.princeton.edu:8888"
LEAN_GATEWAY_URL = os.environ.get("LEAN_GATEWAY_URL", "http://della9.princeton.edu:9876")
# LEAN_GATEWAY_URL = "http://della9.princeton.edu:9876"
#MODEL_NAME = "Goedel-Prover-V2-32B" # Or the model you are using
MODEL_NAME= "Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80"

# --- Main Test Runner ---
async def simple_test_lightweight():
    """
    Sets up real schedulers and runs an integration test of the 
    lightweight_inference function.
    """
    
    # Instantiate the real scheduler services
    inference_scheduler = InferenceSchedulerService(vllm_gateway_url=LLM_GATEWAY_URL)
    compilation_scheduler = CompilationSchedulerService(compilation_gateway_url=LEAN_GATEWAY_URL)

    inference_scheduler.start()
    
    # --- Test Data ---
    problem_statement = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat Polynomial Complex\n\ntheorem easyproblem (a b : ℕ) : a + b = b + a := by sorry"
    problem_name = "easy_problem"
    num_revisions = 3
    print("\n" + "="*50)
    print("🚀 RUNNING LIVE INTEGRATION TEST...")
    print(f"   Problem: {problem_statement}")
    print(f"   Revisions: {num_revisions}")
    print("="*50)
    
    final_result = None
    try:
        # Call the function with the real services
        final_result = await lightweight_inference(
            inference_scheduler=inference_scheduler,
            compilation_scheduler=compilation_scheduler,
            problem_statement=problem_statement,
            problem_name=problem_name,
            model_name=MODEL_NAME,
            num_of_revision=num_revisions,
            num_of_passes=8
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred during the test: {e}", exc_info=True)
    finally:
        # Gracefully stop the background workers in the schedulers
        inference_scheduler.stop()
        compilation_scheduler.stop()
        logging.info("Scheduler workers stopped.")

    print("\n--- FINAL RESULT ---")
    if final_result:
        pprint(final_result)
        if final_result.get("compilation_result", {}).get("complete"):
            print("\n✅ Test Concluded: A complete proof was found!")
            print(f"{final_result['code']}")
        else:
            print("\n⏹️ Test Concluded: A complete proof was not found after all revisions.")
    else:
        print("\n❌ Test Failed: An error occurred during execution.")

async def test_lightweight_putnam(args):
    #putnam_problem_path = "/scratch/gpfs/haoyu/Test-time/test/minif2f_scaffolded_lemmas.jsonl"
    #putnam_problem_path = '/scratch/gpfs/haoyu/Test-time/test/omni_scaffolded_lemmas.jsonl'
    putnam_problem_path = args.putnam_problem_path
    MODEL_NAME = args.model_name

    df = pd.read_json(putnam_problem_path, lines=True)

    #df = df[:2]

    # Instantiate the real scheduler services
    inference_scheduler = InferenceSchedulerService(vllm_gateway_url=LLM_GATEWAY_URL, num_workers=350)
    compilation_scheduler = CompilationSchedulerService(compilation_gateway_url=LEAN_GATEWAY_URL, num_workers=350)

    inference_scheduler.start()

    num_revisions = args.num_revisions
    num_passes = args.num_passes

    use_lemma = args.use_lemma

    print(f"starting inference on {putnam_problem_path}")
    print(f"use lemma: {use_lemma}")
    print(f"model name: {MODEL_NAME}")
    print(f"num passes: {num_passes}, num revisions: {num_revisions}")

    # num_revisions = 0
    # num_passes = 128

    tasks = [
        asyncio.create_task(lightweight_inference(
            inference_scheduler=inference_scheduler,
            compilation_scheduler=compilation_scheduler,
            problem_statement=r['lean4_code'],
            problem_name=r['problem_id'],
            model_name=MODEL_NAME,
            num_of_revision=num_revisions,
            num_of_passes=num_passes,
            problem_index=i+1,
            facts=r['lemmas'] if use_lemma else [],
        ))
        for i, r in df.iterrows()
    ]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        print("\n--- Shutdown signal received, cancelling all background tasks ---")
        
        # Iterate through all running tasks and cancel them
        for task in tasks:
            task.cancel()
        
        # Wait for all tasks to acknowledge the cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        inference_scheduler.stop()
        
        print("--- All tasks have been shut down. Exiting. ---")

    total_count = 0
    for r in results:
        try:
            complete = r['compilation_result']['complete']
            if complete:
                total_count += 1
                print("\n\n\n")
                print({r["code"]})
        except:
            continue
    print(f"num passes: {num_passes}, num revisions: {num_revisions}")
    print(f"total solved problems: {total_count}, solved_ratio: {total_count/len(df)}")


    # for r in results:
    #     try:
    #         print("\n\n\n")
    #         print(r)
    #     except:
    #         continue

# --- Run the test ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run lightweight inference tests.")
    # parser.add_argument("--putnam_problem_path", type=str, default="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_misleading.jsonl", help="Path to the Putnam problem JSONL file.")
    # parser.add_argument("--putnam_problem_path", type=str, default="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading.jsonl", help="Path to the Putnam problem JSONL file.")
    parser.add_argument("--putnam_problem_path", type=str, default="/scratch/gpfs/CHIJ/st3812/projects/Test-time/dataset/minif2f_32b_solve_8b_not_solve_drop_09_misleading_3times.jsonl", help="Path to the Putnam problem JSONL file.")
    parser.add_argument("--model_name", type=str, default="Goedel-Prover-V2-8B-reformat_revision_v2_S80-merge80", help="Name of the model to use for inference.")
    parser.add_argument("--num_revisions", type=int, default=0, help="Number of revisions to attempt.")
    parser.add_argument("--num_passes", type=int, default=32, help="Number of parallel passes to run.")
    parser.add_argument("--use_lemma", action='store_true', help="Whether to use lemmas from the dataset.")
    args = parser.parse_args()

    try:
        asyncio.run(test_lightweight_putnam(args))
    except KeyboardInterrupt:
        print("Application forcefully interrupted.")