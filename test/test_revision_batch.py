import asyncio
import logging
import json
import argparse  # Added for command-line arguments

# --- Basic Configuration ---
logger = logging.getLogger(__name__)

# Assuming this import path is correct for your project structure
from scheduler.scheduler_service import InferenceSchedulerService, CompilationSchedulerService

async def process_prompts_from_file(
    scheduler: InferenceSchedulerService, 
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
                
                # Create a task for each prompt.
                # You can customize the model and params here if needed.
                tasks.append(
                    scheduler.inference(
                        prompt=data['prompt'],
                        model="gpt-oss-120b", 
                        extra_params={"temperature": 1.0}
                    )
                )

    print(f"Submitting {len(tasks)} inference tasks to the scheduler...")
    
    # 2. Run all tasks concurrently and wait for the results
    results = await asyncio.gather(*tasks)
    
    print("All inference tasks are complete. Writing results to output file...")

    # 3. Combine original data with the new generations and write to the output file
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for original_data, generation_result in zip(input_data_list, results):
            # Append the new 'generation' field
            original_data['generation'] = generation_result
            # Write the updated dictionary as a new line in the output file
            f_out.write(json.dumps(original_data) + '\n')
            
    print(f"✅ Successfully saved results to: {output_file}")


async def main():
    # --- Set up Command Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Run asynchronous inference on prompts from a JSONL file.")
    parser.add_argument('--input-file', type=str, required=True, help='Path to the input JSONL file.')
    parser.add_argument('--output-file', type=str, required=True, help='Path to save the output JSONL file.')
    parser.add_argument('--vllm-gateway-url', type=str, default='http://della-gpu.princeton.edu:8888', help='URL of the vLLM gateway.')
    parser.add_argument('--num-workers', type=int, default=40, help='Number of concurrent workers for the scheduler.')
    
    args = parser.parse_args()

    # --- Initialize and Start the Scheduler ---
    scheduler = InferenceSchedulerService(
        vllm_gateway_url=args.vllm_gateway_url, 
        num_workers=args.num_workers
    )
    scheduler.start()

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