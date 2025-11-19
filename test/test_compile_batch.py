import asyncio
import logging
import json
import argparse  # Added for command-line arguments
import re
# --- Basic Configuration ---
logger = logging.getLogger(__name__)

# Assuming this import path is correct for your project structure
from scheduler.scheduler_service import InferenceSchedulerService, CompilationSchedulerService

from proofsearch.lightweight.lightweight_utils import InferenceHandler, RevisionHandler

import re

def extract_first_lean4_block(text: str) -> str | None:
    """
    Extracts the content from the first lean4 code block in a string.

    Args:
        text: The string to search within.

    Returns:
        The extracted code as a string, or None if no block is found.
    """
    # This regex finds ```lean4, captures everything until the next ```,
    # and does so in a non-greedy way (the '?').
    pattern = r"```lean4([\s\S]*?)```"
    
    match = re.search(pattern, text)
    
    if match:
        # The content inside the parentheses is the first captured group.
        # .strip() removes leading/trailing whitespace like newlines.
        return match.group(1).strip()
    
    return None


async def process_prompts_from_file(
    scheduler: CompilationSchedulerService, 
    input_file: str, 
    output_file: str
):
    """
    Reads prompts from a .jsonl file, sends them for inference,
    and writes the results to an output .jsonl file.
    """
    print(f"Reading prompts from: {input_file}")
    
    # 1. Read all data from the input file and create inference tasks
    input_data_list = []
    tasks = []
    with open(input_file, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            if line.strip():  # Ensure the line is not empty
                data = json.loads(line)
                input_data_list.append(data)

                inference_output = data["generation"]

                if "problem_statement" not in data:
                    if "turns" in data:
                        prompt = data["turns"][0]["user"]
                    else:
                        prompt = data["prompt"]
                    problem_statement = extract_first_lean4_block(prompt)
                else:
                    problem_statement = data["problem_statement"]





                name = data.get("problem_id","")
                
                lean_code = InferenceHandler.process_output(inference_output, problem_statement)
                # Create a task for each prompt.
                # You can customize the model and params here if needed

                tasks.append(
                    scheduler.compile(
                        name=name, 
                        code=lean_code
                    ) 
                )


    print(f"Submitting {len(tasks)} compile tasks to the scheduler...")
    
    # 2. Run all tasks concurrently and wait for the results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("All compile tasks are complete. Writing results to output file...")

    # 3. Combine original data with the new generations and write to the output file
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for original_data, result in zip(input_data_list, results):
            if isinstance(result, Exception):
                # It was an error, log it or save an error message
                error_info = {"error": str(result)}
                original_data['compilation_result'] = error_info
                logger.error(f"Task for {original_data.get('problem_id', 'N/A')} failed: {result}")
            else:
                # It was a success
                original_data['compilation_result'] = result
            f_out.write(json.dumps(original_data) + '\n')
            
    print(f"✅ Successfully saved results to: {output_file}")


async def main():
    # --- Set up Command Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Run asynchronous inference on prompts from a JSONL file.")
    parser.add_argument('--input-file', type=str, required=True, help='Path to the input JSONL file.')
    parser.add_argument('--output-file', type=str, required=True, help='Path to save the output JSONL file.')
    parser.add_argument('--compilation-gateway-url', type=str, default='http://della9.princeton.edu:9876', help='URL of the vLLM gateway.')
    parser.add_argument('--num-workers', type=int, default=24, help='Number of concurrent workers for the scheduler.')
    
    args = parser.parse_args()

    # --- Initialize and Start the Scheduler ---
    scheduler = CompilationSchedulerService(
        compilation_gateway_url=args.compilation_gateway_url, 
        num_workers=args.num_workers
    )
    # scheduler.start()

    # --- Run the File Processing Task ---
    await process_prompts_from_file(
        scheduler=scheduler,
        input_file=args.input_file,
        output_file=args.output_file
    )

    scheduler.stop()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO) # Set level to INFO to see print statements
    asyncio.run(main())