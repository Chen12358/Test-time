# test/test_mediumweight_batch.py

import asyncio
import logging
import argparse
import itertools
import pandas as pd
from jload import jsave

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Import the REAL services and the function to test ---
from scheduler.scheduler_service import InferenceSchedulerService, CompilationSchedulerService
from proofsearch.mediumweight.mediumweightsearch import mediumweight_inference

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)

# The URLs for your running services
# LLM_GATEWAY_URL = "http://della9.princeton.edu:6666"
# LEAN_GATEWAY_URL = "http://della9.princeton.edu:9876"

LLM_GATEWAY_URL = "http://della-gpu.princeton.edu:8888"
LEAN_GATEWAY_URL = os.environ.get("LEAN_GATEWAY_URL", "http://della9.princeton.edu:9876")
# LEAN_GATEWAY_URL = "http://della-gpu.princeton.edu:9876"

async def test_mediumweight_batch(args):
    """
    Runs a batch integration test of the mediumweight_inference function on a
    dataset of problems.
    """
    df = pd.read_json(args.problem_path, lines=True) if args.problem_path.endswith('.jsonl') else pd.read_json(args.problem_path)

    # Instantiate the real scheduler services with a high number of workers for concurrency
    # inference_scheduler = InferenceSchedulerService(vllm_gateway_url=LLM_GATEWAY_URL, num_workers=1000)
    # compilation_scheduler = CompilationSchedulerService(compilation_gateway_url=LEAN_GATEWAY_URL, num_workers=900)
    inference_scheduler = InferenceSchedulerService(vllm_gateway_url=LLM_GATEWAY_URL, num_workers=350)
    compilation_scheduler = CompilationSchedulerService(compilation_gateway_url=LEAN_GATEWAY_URL, num_workers=450)
    # inference_scheduler = InferenceSchedulerService(vllm_gateway_url=LLM_GATEWAY_URL, num_workers=200)
    # compilation_scheduler = CompilationSchedulerService(compilation_gateway_url=LEAN_GATEWAY_URL, num_workers=200)


    inference_scheduler.start()

    print("\n" + "="*80)
    print("🚀 RUNNING MEDIUM-WEIGHT BATCH TEST...")
    print(f"   Dataset: {args.problem_path}")
    print(f"   Model: {args.model_name}")
    print(f"   Parallel Passes per Problem: {args.num_passes}")
    print(f"   Revisions per Subproblem: {args.num_revisions}")
    print("="*80 + "\n")

    # Create a list of concurrent tasks, one for each problem in the dataset
    tasks = [
        asyncio.create_task(mediumweight_inference(
            inference_scheduler=inference_scheduler,
            compilation_scheduler=compilation_scheduler,
            problem_statement=row['lean4_code'],
            problem_name=row['problem_id'] if 'problem_id' in row else row['name'],
            model_name=args.model_name,
            num_of_revision=args.num_revisions,
            num_of_passes=args.num_passes,
            problem_index=i + 1,
            facts=row.get('facts', []) if args.use_facts else []
        ))
        for i, row in itertools.islice(df.iterrows(), args.limit) # Use islice to limit problems
    ]

    results = []
    try:
        # Gather results from all problem-solving tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logging.error(f"A critical error occurred in asyncio.gather: {e}", exc_info=True)
    finally:
        print("\n--- Shutting down schedulers ---")
        inference_scheduler.stop()
        compilation_scheduler.stop()
        print("--- Schedulers stopped ---")

    # --- Process and Summarize Results ---
    total_solved = 0
    for res in results:
        if isinstance(res, Exception):
            logging.error(f"A task resulted in an exception: {res}")
            continue
        
        if res.get("compilation_result", {}).get("complete"):
            total_solved += 1
            print("\n" + "-"*20 + f" ✅ SUCCESS: {res.get('name')} " + "-"*20)
            print(res.get("code"))
            print("-" * (42 + len(res.get('name', ''))))

    jsave(results, args.output_path)
    print(f"\n--- Results saved to {args.output_path} ---")

    num_problems = len(tasks)
    solve_ratio = (total_solved / num_problems) * 100 if num_problems > 0 else 0

    print("\n" + "="*80)
    print("📊 BATCH TEST SUMMARY")
    print("="*80)
    print(f"   Total problems attempted: {num_problems}")
    print(f"   Total problems solved: {total_solved}")
    print(f"   Solve Ratio: {solve_ratio:.2f}%")
    print("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run medium-weight inference batch tests.")
    parser.add_argument("--problem_path", type=str, default="mediumweight_batch_results_33_with_facts.json", help="Path to the problem JSONL file.")
    parser.add_argument("--output_path", type=str, default="mediumweight_batch_results_332.json", help="Path to save the results JSON file.")
    parser.add_argument("--model_name", type=str, default="SFT_147K_RL_S80_fix", help="Name of the model to use.")
    parser.add_argument("--num_revisions", type=int, default=2, help="Number of revisions for each subproblem.")
    parser.add_argument("--num_passes", type=int, default=8, help="Number of parallel passes for each problem.")
    parser.add_argument("--limit", type=int, default=250, help="Limit the number of problems to test from the dataset.")
    parser.add_argument("--use_facts", action='store_true', help="Whether to use facts provided in the dataset.")
    args = parser.parse_args()

    try:
        asyncio.run(test_mediumweight_batch(args))
    except KeyboardInterrupt:
        print("\n🛑 Application forcefully interrupted by user.")