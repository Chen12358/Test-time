import asyncio
import logging
from typing import Dict, Any, List
from jload import jload, jsave

from proofsearch.lightweight.lightweightsearch import lightweight_inference
from proofsearch.lightweight.lightweight_utils import (
    InferenceHandler,
    extract_content_from_inference_result,
    extract_usage_from_inference_result,
    accumulate_usage
)
from .utils import ProofAnalysis

logger = logging.getLogger(__name__)

async def mediumweight_inference_single(
    inference_scheduler,
    compilation_scheduler,
    problem_statement: str,
    problem_name: str,
    model_name: str,
    num_of_revision: int = 2,
    num_of_passes: int = 8,
    problem_index: int = 1,
    max_tokens: int = 24000,
    temperature: float = 1.0,
    top_p: float = 1.0,
    shared_token_usage: dict = None,
    facts: List[str] = []
) -> Dict[str, Any]:
    """
    Implements the medium-weight proof search pipeline.

    1.  Generates an initial, full proof attempt which may contain multiple lemmas.
    2.  If errors exist, it analyzes the proof to find faulty lemmas.
    3.  For each faulty lemma, it creates a subproblem.
    4.  It uses the lightweight_inference pipeline to solve all subproblems in parallel.
    5.  It reconstructs the full proof with the fixed lemmas.
    """
    execution_log: List[str] = []
    correct_lemmas: List[Dict[str, str]] = []

    # --- 1. Initial Full Proof Generation ---
    execution_log.append(f"[{problem_name}] Starting initial full proof generation.")
    
    initial_prompt = InferenceHandler.format_input(problem_statement, facts=facts)
    
    extra_params = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }

    try:
        inference_result = await inference_scheduler.inference(
            prompt=initial_prompt,
            model=model_name,
            priority=problem_index,
            extra_params=extra_params
        )
        
        initial_output = extract_content_from_inference_result(inference_result)
        usage = extract_usage_from_inference_result(inference_result)
        if shared_token_usage is not None:
            accumulate_usage(shared_token_usage, usage)
        
        initial_code = InferenceHandler.process_output(initial_output, problem_statement, facts=facts)
    except asyncio.CancelledError:
        execution_log.append(f"[{problem_name}] Task cancelled during initial inference.")
        logger.info(f"Task {problem_name} cancelled.")
        raise
    except Exception as e:
        error_msg = f"Initial inference failed: {e}"
        logger.error(f"[{problem_name}] {error_msg}", exc_info=True)
        execution_log.append(f"ERROR: {error_msg}")
        return {
            "name": problem_name, 
            "code": "", 
            "compilation_result": {"complete": False, "pass": False, "errors": []}, 
            "execution_log": execution_log,
            "correct_lemmas": correct_lemmas
        }

    # --- 2. Initial Compilation and Analysis ---
    execution_log.append(f"[{problem_name}] Compiling the initial full proof.")
    try:
        compilation_info = await compilation_scheduler.compile(name=f"{problem_name}_initial", code=initial_code)
        compilation_result = compilation_info.get('compilation_result', {})
    except asyncio.CancelledError:
        execution_log.append(f"[{problem_name}] Task cancelled during initial compilation.")
        logger.info(f"Task {problem_name} cancelled.")
        raise
    except Exception as e:
        error_msg = f"Initial compilation failed: {e}"
        logger.error(f"[{problem_name}] {error_msg}", exc_info=True)
        execution_log.append(f"ERROR: {error_msg}")
        compilation_result = {"complete": False, "pass": False, "errors": []}
    
    logger.info(f"[{problem_name}] Initial compilation result: {compilation_result}")

    if compilation_result.get('complete'):
        # execution_log.append(f"[{problem_name}] Success on the first attempt!")
        # analysis = ProofAnalysis(initial_code, [], compilation_scheduler)
        # await analysis.verify_all_lemmas()
        # fully_correct_lemmas = analysis.get_fully_correct_lemmas()
        # for lemma_info in fully_correct_lemmas:
        #     correct_lemmas.append({
        #         'name': lemma_info['name'],
        #         'type': lemma_info['type'],
        #         'statement': lemma_info['statement'],
        #         'source': 'initial_attempt',
        #         'dependencies': lemma_info['dependencies'],
        #         'direct_dependencies': lemma_info['direct_dependencies']
        #     })
        
        return {
            "name": problem_name, 
            "code": initial_code, 
            "compilation_result": compilation_result, 
            "execution_log": execution_log,
            "correct_lemmas": []
        }

    if not compilation_result.get('errors'):
        execution_log.append(f"WARN: [{problem_name}] Initial proof is not complete but has no errors. Cannot proceed.")
        return {
            "name": problem_name, 
            "code": initial_code, 
            "compilation_result": compilation_result, 
            "execution_log": execution_log,
            "correct_lemmas": correct_lemmas
        }

    # --- 3. Deconstruct into Subproblems ---
    execution_log.append(f"[{problem_name}] Initial proof has errors. Analyzing and deconstructing.")
    analysis = ProofAnalysis(initial_code, compilation_result.get('errors'), compilation_scheduler)
    await analysis.verify_all_lemmas()
    
    fully_correct_lemmas = analysis.get_fully_correct_lemmas()
    for lemma_info in fully_correct_lemmas:
        correct_lemmas.append({
            'name': lemma_info['name'],
            'type': lemma_info['type'],
            'statement': lemma_info['statement'],
            'source': 'initial_attempt_correct',
            'dependencies': lemma_info['dependencies'],
            'direct_dependencies': lemma_info['direct_dependencies']
        })
    
    error_lemmas = analysis.get_error_lemmas_sorted()
    if not error_lemmas:
        execution_log.append(f"WARN: [{problem_name}] Compilation failed but no specific error lemmas were identified.")
        return {
            "name": problem_name, 
            "code": initial_code, 
            "compilation_result": compilation_result, 
            "execution_log": execution_log, 
            "final_analysis_report": analysis.report_json(),
            "correct_lemmas": correct_lemmas
        }

    # --- 4. Asynchronously Fix Subproblems ---
    execution_log.append(f"[{problem_name}] Identified {len(error_lemmas)} faulty lemmas to fix in parallel: {', '.join(error_lemmas)}")
    
    fix_tasks = []
    for lemma_name in error_lemmas:
        try:
            subproblem_statement, subproblem_facts= analysis.construct_subproblem(lemma_name)
            subproblem_name = f"{problem_name}_fix_{lemma_name}"
            
            task = asyncio.create_task(lightweight_inference(
                inference_scheduler=inference_scheduler,
                compilation_scheduler=compilation_scheduler,
                problem_statement=subproblem_statement,
                problem_name=subproblem_name,
                model_name=model_name,
                num_of_revision=num_of_revision,
                num_of_passes=num_of_passes,
                problem_index=problem_index,
                facts=facts + subproblem_facts,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            ))
            fix_tasks.append((lemma_name, task))
        except ValueError as e:
            error_msg = f"Could not construct subproblem for {lemma_name}: {e}"
            logger.error(f"[{problem_name}] {error_msg}")
            execution_log.append(f"ERROR: {error_msg}")

    if fix_tasks:
        try:
            task_results = await asyncio.gather(*(task for _, task in fix_tasks), return_exceptions=True)
            
            all_successful = True
            for (lemma_name, _), result in zip(fix_tasks, task_results):
                if isinstance(result, dict) and 'token_usage' in result and shared_token_usage is not None:
                    accumulate_usage(shared_token_usage, result['token_usage'])
                
                if isinstance(result, asyncio.CancelledError):
                    execution_log.append(f"[{problem_name}] Subproblem fix for '{lemma_name}' was cancelled.")
                    continue
                    
                if isinstance(result, Exception):
                    all_successful = False
                    error_msg = f"Fixing task for '{lemma_name}' failed with an exception: {result}"
                    execution_log.append(f"ERROR: {error_msg}")
                    logger.error(f"[{problem_name}] {error_msg}", exc_info=result)
                    continue

                if result.get("compilation_result", {}).get("complete"):
                    execution_log.append(f"Successfully fixed lemma '{lemma_name}'.")
                    fixed_code = result.get("code", "")
                    await analysis.fix_lemma(lemma_name, fixed_code)
                    
                    temp_analysis = ProofAnalysis(fixed_code, [], compilation_scheduler)
                    fully_correct_lemmas_fixed = temp_analysis.get_fully_correct_lemmas()
                    for lemma_info in fully_correct_lemmas_fixed:
                        correct_lemmas.append({
                            'name': lemma_info['name'],
                            'type': lemma_info['type'],
                            'statement': lemma_info['statement'],
                            'source': f'fixed_subproblem_{lemma_name}',
                            'dependencies': lemma_info['dependencies'],
                            'direct_dependencies': lemma_info['direct_dependencies']
                        })
                else:
                    all_successful = False
                    execution_log.append(f"Failed to fix lemma '{lemma_name}'. Lightweight search did not find a complete proof.")
            
            if not all_successful:
                execution_log.append("Aborting medium-weight search due to failure in fixing one or more subproblems.")
                return {
                    "name": problem_name,
                    "code": analysis.code,
                    "compilation_result": {"complete": False, "pass": False, "errors": []},
                    "final_analysis_report": analysis.report_json(),
                    "execution_log": execution_log,
                    "correct_lemmas": correct_lemmas
                }
                
        except asyncio.CancelledError:
            execution_log.append(f"[{problem_name}] Cancelling all lightweight inference subtasks.")
            for lemma_name, task in fix_tasks:
                if not task.done():
                    task.cancel()
                    logger.info(f"[{problem_name}] Cancelled lightweight task for lemma '{lemma_name}'")
            
            await asyncio.gather(*(task for _, task in fix_tasks), return_exceptions=True)
            logger.info(f"Task {problem_name} cancelled.")
            raise
        finally:
            for lemma_name, task in fix_tasks:
                if not task.done():
                    task.cancel()

    # --- 5. Final Verification and Return ---
    final_code = analysis.code
    execution_log.append(f"[{problem_name}] All faulty lemmas have been patched. Performing final verification.")
    
    try:
        final_compilation_info = await compilation_scheduler.compile(name=f"{problem_name}_final", code=final_code)
        final_compilation_result = final_compilation_info.get('compilation_result', {})
    except asyncio.CancelledError:
        execution_log.append(f"[{problem_name}] Task cancelled during final compilation.")
        logger.info(f"Task {problem_name} cancelled.")
        raise
    except Exception as e:
        error_msg = f"Final verification failed with an exception: {e}"
        logger.error(f"[{problem_name}] {error_msg}", exc_info=True)
        execution_log.append(f"ERROR: {error_msg}")
        final_compilation_result = {"complete": False, "pass": False, "errors": []}

    if final_compilation_result.get('complete'):
        execution_log.append(f"[{problem_name}] Medium-weight search successful! Final proof is correct.")
    else:
        execution_log.append(f"WARN: [{problem_name}] Medium-weight search finished, but final proof is still not correct.")
        jsave(analysis.report_json(), f"{problem_name}_failed_analysis.json")

    return {
        "name": problem_name,
        "code": final_code,
        "compilation_result": final_compilation_result,
        "final_analysis_report": analysis.report_json(),
        "execution_log": execution_log,
        "correct_lemmas": correct_lemmas
    }

async def mediumweight_inference(
    inference_scheduler,
    compilation_scheduler,
    problem_statement: str,
    problem_name: str,
    model_name: str,
    num_of_revision: int = 1,
    num_of_passes: int = 4,
    problem_index: int = 1,
    max_tokens: int = 24000,
    temperature: float = 1.0,
    top_p: float = 1.0,
    facts: List[str] = []
) -> dict:
    """
    Orchestrates multiple parallel passes of the medium-weight inference pipeline.

    This function launches `num_of_passes` instances of `mediumweight_inference_single`
    concurrently. If any pass successfully finds a complete proof, all other
    running passes are immediately cancelled to save resources.

    Args:
        num_of_passes: The number of parallel proof search attempts.
        (Other args are passed down to the single-pass function)

    Returns:
        A dictionary with the result of the first successful pass, or the result
        of the first completed pass if none were successful.
    """
    problem_name_list = [f"{problem_name}_pass{i}" for i in range(num_of_passes)]
    
    combined_token_usage = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0
    }

    all_passes_correct_lemmas = []  # List of dicts: {'pass_id': int, 'pass_name': str, 'lemmas': [...]}

    task_list = [
        asyncio.create_task(mediumweight_inference_single(
            inference_scheduler=inference_scheduler,
            compilation_scheduler=compilation_scheduler,
            problem_statement=problem_statement,
            problem_name=problem_name_i,
            model_name=model_name,
            num_of_revision=num_of_revision,
            num_of_passes=4,
            problem_index=problem_index,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            shared_token_usage=combined_token_usage,
            facts=facts
        ))
        for problem_name_i in problem_name_list
    ]

    successful_result = None
    completed_results = []
    pass_index = 0  # Track which pass each result comes from

    for future in asyncio.as_completed(task_list):
        try:
            result = await future
            completed_results.append(result)

            if 'correct_lemmas' in result:
                # 找到这个result对应的pass index
                result_pass_name = result.get('name', '')
                pass_id = -1
                for i, pname in enumerate(problem_name_list):
                    if pname == result_pass_name:
                        pass_id = i
                        break
                
                all_passes_correct_lemmas.append({
                    'pass_id': pass_id,
                    'pass_name': result_pass_name,
                    'lemmas': result['correct_lemmas'],
                    'compilation_successful': result.get("compilation_result", {}).get("complete", False)
                })

            if result.get("compilation_result", {}).get("complete"):
                logger.info(f"Success for {problem_name} in one of the passes. Cancelling remaining tasks.")
                successful_result = result
                for task in task_list:
                    if not task.done():
                        task.cancel()
                break
        except asyncio.CancelledError:
            logger.info(f"A pass for {problem_name} was cancelled because a solution was found elsewhere.")
        except Exception as e:
            logger.error(f"A medium-weight pass for {problem_name} failed with an exception: {e}", exc_info=True)

    await asyncio.gather(*task_list, return_exceptions=True)

    lemma_collection_summary = {
        'total_passes': len(problem_name_list),
        'completed_passes': len(all_passes_correct_lemmas),
        'passes_with_lemmas': [p for p in all_passes_correct_lemmas if p['lemmas']],
        'all_passes_lemmas': all_passes_correct_lemmas
    }

    if successful_result:
        successful_result['name'] = problem_name
        successful_result['token_usage'] = combined_token_usage
        successful_result['lemma_collection'] = lemma_collection_summary
        return successful_result

    logger.warning(f"No successful proof found for {problem_name} after {num_of_passes} passes.")
    if completed_results:
        first_result = completed_results[0]
        first_result['name'] = problem_name
        first_result['token_usage'] = combined_token_usage
        first_result['lemma_collection'] = lemma_collection_summary
        return first_result
    else:
        return {
            "name": problem_name,
            "code": "",
            "compilation_result": {"complete": False, "pass": False, "errors": []},
            "execution_log": ["All medium-weight passes failed catastrophically."],
            "token_usage": combined_token_usage,
            "lemma_collection": lemma_collection_summary
        }