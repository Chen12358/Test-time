import asyncio

import logging

from .lightweight_utils import (
    InferenceHandler, 
    RevisionHandler,
    extract_content_from_inference_result,
    extract_usage_from_inference_result,
    accumulate_usage,
    accumulate_result
)

# --- Basic Configuration ---
logger = logging.getLogger(__name__)

P_INITIAL = 16

async def lightweight_inference_single(
    inference_scheduler, 
    compilation_scheduler, 
    problem_statement: str, 
    problem_name: str, 
    model_name: str, 
    result_file_name: str = "",
    # axioms: list = [],
    num_of_revision: int = 2,
    problem_index: int = 1,
    facts: list = None,
    max_tokens: int = 24000,
    temperature: float = 1.0,
    top_p: float = 1.0,
    shared_token_usage: dict = None,  # Shared token usage parameter
) -> dict:
    """
    Performs an initial inference and compilation, followed by a series of revisions.

    Returns:
        A dictionary containing the final code and compilation result.
        Token usage is accumulated directly to shared_token_usage if provided.
    """
    # --- 1. Initial Inference and Compilation ---
    logger.info(f"Starting initial inference for problem: {problem_name}")
    inference_input = InferenceHandler.format_input(problem_statement, facts)

    # for larger problems index, the priority number will be larger (lower priority)
    base_priority = problem_index * P_INITIAL
    
    extra_params = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }

    # Await the inference result
    num_of_revision_left = num_of_revision
    # if during the initial inference, exception/error happens, then just retry
    # make the number of revisions left smaller (such that the total number of inference is bounded)
    while num_of_revision_left >= 0:
        try:
            inference_result = await inference_scheduler.inference(
                prompt=inference_input, 
                model=model_name, 
                priority=base_priority,
                extra_params=extra_params
            )
            
            # Extract content and usage
            initial_output = extract_content_from_inference_result(inference_result)
            usage = extract_usage_from_inference_result(inference_result)
            # Accumulate to shared usage if provided
            if shared_token_usage is not None:
                accumulate_usage(shared_token_usage, usage)
            
            lean_code = InferenceHandler.process_output(initial_output, problem_statement, facts)
            break
        except asyncio.CancelledError:
            # Token usage already accumulated, just re-raise
            logger.info(f"Task {problem_name} was cancelled during initial inference.")
            raise
        except Exception as e:
            logger.warning(f"An error occurred during initial inference for {problem_name}: {e}")
            num_of_revision_left -= 1
            if num_of_revision_left >= 0:
                logger.warning(f"retry initial inference, num of revision left: {num_of_revision_left}")
            else:
                # if error happens at initial inference, then probably should just return
                return {
                    "code": "", 
                    "compilation_result": {"pass": False, "complete": False, "errors": [f"Initial inference failed: {e}"]}
                }
    compilable_code = lean_code  # Placeholder for any additional synchronous code processing

    logger.debug(compilable_code)

    # Await the compilation result
    logger.info(f"Submitting initial proof for {problem_name} for compilation...")
    try:
        compilation_info = await compilation_scheduler.compile(name=problem_name, code=compilable_code)
    except asyncio.CancelledError:
        logger.info(f"Task {problem_name} was cancelled during initial compilation.")
        raise
    except Exception as e:
        logger.error(f"An error occurred during initial compilation for {problem_name}: {e}")
        parsed_result = {"pass": False, "complete": False, "system_errors": [f"Initial compilation failed: {e}"]}
        # use this error to go to the next revision
        compilation_info = {"code": compilable_code, "compilation_result": parsed_result}
    
    # Safely extract the nested result dictionary
    compilation_result = compilation_info.get('compilation_result', {}) if compilation_info else {}

    compilation_dict = {
            "name": problem_name, 
            "code": compilable_code, 
            "compilation_result": compilation_result
        }

    accumulate_result(result_file_name, compilation_dict)

    # If the first attempt is a complete proof, we're done!
    if compilation_result.get('complete'):
        logger.info(f"\n\n\nSuccess on first attempt for {problem_name}!\n\n\n")
        logger.info(f'{compilable_code}\n\n\n')
        return {
            "name": problem_name, 
            "code": compilable_code, 
            "compilation_result": compilation_result
        }
    
    # --- 2. Revision Loop ---
    last_code = compilable_code
    last_errors = compilation_result.get('errors', [])
    
    for revision_round in range(num_of_revision_left):
        logger.info(f"Starting revision round {revision_round + 1}/{num_of_revision_left} for {problem_name}...")
        
        revision_input = RevisionHandler.format_input(problem_statement, last_code, last_errors, facts)

        logger.debug('\n\n\nrevision input\n\n\n')
        logger.debug(revision_input)
        logger.debug('\n\n\n')
        
        # Await the revision inference, giving it a higher priority
        try:
            revision_result = await inference_scheduler.inference(
                prompt=revision_input, 
                model=model_name, 
                priority=(base_priority-revision_round-1),
                extra_params=extra_params
            )

            # Extract content and usage
            revision_output = extract_content_from_inference_result(revision_result)
            usage = extract_usage_from_inference_result(revision_result)
            # Accumulate to shared usage if provided
            if shared_token_usage is not None:
                accumulate_usage(shared_token_usage, usage)

            if not revision_output:
                logger.warning(f"Revision inference failed for {problem_name} on round {revision_round + 1}.")
                continue # Skip to the next revision attempt
            logger.debug('\n\n\nrevision output\n\n\n')
            logger.debug(revision_output)
            logger.debug('\n\n\n')

            lean_code = RevisionHandler.process_output(revision_output, problem_statement, facts)
        except asyncio.CancelledError:
            logger.info(f"Task {problem_name} was cancelled during revision round {revision_round + 1}.")
            raise
        except Exception as e:
            logger.warning(f"An error occurred during revision round {revision_round+1} for {problem_name}: {e}")
            if revision_round != num_of_revision - 1:
                # just do another revision, skip the current round
                logger.warning(f"use previous code and error")
                continue
            # if error happens in the last revision round, then probably should just return
            return {
                "code": "", 
                "compilation_result": {"pass": False, "complete": False, "errors": [f"Revision inference failed: {e}"]}
            }
        compilable_code = lean_code

        # Await the revised compilation, giving it a unique name for tracking
        revision_name = f"{problem_name}_rev{revision_round + 1}"
        logger.info(f"Submitting revised proof {revision_name} for compilation...")
        try:
            compilation_info = await compilation_scheduler.compile(name=problem_name, code=compilable_code)
        except asyncio.CancelledError:
            logger.info(f"Task {problem_name} was cancelled during revision compilation.")
            raise
        except Exception as e:
            logger.warning(f"An error occurred during revision round {revision_round+1} for {problem_name}: {e}")
            if revision_round != num_of_revision - 1:
                # just do another revision, skip the current round
                logger.warning(f"use previous code and error")
                continue
            parsed_result = {"pass": False, "complete": False, "system_errors": [f"Compilation failed: {e}"]}
            # use this error to go to the next revision
            compilation_info = {"code": compilable_code, "compilation_result": parsed_result}
        
        compilation_result = compilation_info.get('compilation_result', {}) if compilation_info else {}

        compilation_dict = {
                "name": revision_name, 
                "code": compilable_code, 
                "compilation_result": compilation_result
            }

        accumulate_result(result_file_name, compilation_dict)

        # If a revision is a complete proof, we're done!
        if compilation_result.get('complete'):
            logger.info(f"\n\n\nSuccess on revision {revision_round + 1} for {problem_name}!\n\n\n")
            logger.info(f'{compilable_code}\n\n\n')
            return {
                "name": problem_name, 
                "code": compilable_code, 
                "compilation_result": compilation_result
            }
        
        # Update state for the next loop iteration
        last_code = compilable_code
        last_errors = compilation_result.get('errors', [])
    
    # --- 3. Final Return ---
    # If no attempt succeeded, return the result of the last revision attempt
    logger.info(f"Lightweight search for {problem_name} concluded without a complete proof.")
    return {
        "name": problem_name, 
        "code": last_code, 
        "compilation_result": compilation_result
    }

async def lightweight_inference(inference_scheduler, 
    compilation_scheduler, 
    problem_statement: str, 
    problem_name: str, 
    model_name: str, 
    result_file_name: str = "",
    # axioms: list = [],
    num_of_revision: int = 2,
    num_of_passes: int = 8,
    problem_index: int = 1,
    facts: list = None,
    max_tokens: int = 24000,
    temperature: float = 1.0,
    top_p: float = 1.0,
) -> dict:
    problem_name_list = [f"{problem_name}_pass{i}" for i in range(num_of_passes)]
    
    # Initialize combined token usage (shared across all passes)
    combined_token_usage = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0
    }
    
    # create tasks - pass shared token usage to each task
    task_list = [
        asyncio.create_task(lightweight_inference_single(
            inference_scheduler,
            compilation_scheduler, 
            problem_statement, 
            problem_name_i, 
            model_name, 
            result_file_name,
            # axioms,
            num_of_revision,
            problem_index,
            facts,
            max_tokens,
            temperature,
            top_p,
            shared_token_usage=combined_token_usage  # Pass shared usage
        )) 
        for problem_name_i in problem_name_list
    ]
    return_dict = dict()
    completed_results = []
    success = False

    # iterate over task as they complete
    for future in asyncio.as_completed(task_list):
        try:
            result = await future
            completed_results.append(result)
            
            if result['compilation_result']["complete"]:
                return_dict = result
                success = True
                # cancel tasks
                for t in task_list:
                    if not t.done():
                        t.cancel()
                break
        except asyncio.CancelledError:
            logger.info("A task was cancelled because a solution was found.")
            # Token usage was already accumulated to shared dict, no need to do anything
        except Exception as e:
            logger.error(f"A task failed with an exception: {e}")
    
    # Wait for all tasks to finish (including cancelled ones)
    await asyncio.gather(*task_list, return_exceptions=True)
    
    # At this point, combined_token_usage contains all token usage from all passes
    # including those that were cancelled
    
    if not success:
        logger.info("No task succeeded with a complete proof.")
        if completed_results:
            logger.info("Returning the first result from the completed passes.")
            return_dict = completed_results[0]
        else:
            # This handles the edge case where all tasks failed with exceptions
            logger.warning("No results were collected. All tasks may have failed.")
            return_dict = {
                "name": problem_name, 
                "code": "", 
                "compilation_result": {"pass": False, "complete": False, "errors": ["All passes failed to produce a result."]}
            }

    return_dict['name'] = problem_name
    return_dict['token_usage'] = combined_token_usage
    return return_dict