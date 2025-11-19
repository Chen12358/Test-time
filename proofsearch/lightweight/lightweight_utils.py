import logging
import re
from abc import ABC, abstractmethod
import json

from .prompt_templates import INFERENCE_NOFACTS_TEMPLATE, REVISION_NOFACTS_TEMPLATE, INFERENCE_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE,INFERENCE_AXIOMS_LEMMA_OUTPUT_TEMPLATE,REVISION_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE,REVISION_AXIOMS_LEMMA_OUTPUT_TEMPLATE

# --- Basic Configuration ---
logger = logging.getLogger(__name__)

##############################################################
### Functions to process the lean code
##############################################################

DEFAULT_HEADER = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat\n\n"

DEFAULT_HEADER_NO_OPEN = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\n"

def extract_content_from_inference_result(result):
    """
    Extract content from inference result.
    Handles both old format (string) and new format (dict with 'content' and 'usage').
    """
    if isinstance(result, dict):
        return result.get('content', result)
    return result

def extract_usage_from_inference_result(result):
    """
    Extract usage information from inference result.
    Returns a dict with token usage, or empty dict if not available.
    """
    if isinstance(result, dict) and 'usage' in result:
        return result['usage']
    return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

def accumulate_usage(total_usage: dict, new_usage: dict):
    """Accumulate token usage statistics."""
    total_usage['prompt_tokens'] = total_usage.get('prompt_tokens', 0) + new_usage.get('prompt_tokens', 0)
    total_usage['completion_tokens'] = total_usage.get('completion_tokens', 0) + new_usage.get('completion_tokens', 0)
    total_usage['total_tokens'] = total_usage.get('total_tokens', 0) + new_usage.get('total_tokens', 0)

def accumulate_result(file_name: str, new_result: dict):
    """Accumulate all results and write to a file."""
    if file_name == "":
        return
    try:
        # Convert the dictionary to a JSON string
        json_string = json.dumps(new_result)

        # Open the file in append mode and write the JSON string followed by a newline
        with open(file_name, 'a') as f:
            f.write(json_string + '\n')
            
    except (TypeError, IOError) as e:
        logger.error(f"An error occurred while writing to {file_name}: {e}", exc_info=True)




def remove_lean_comments(lean_code: str) -> str:
    """
    Removes single-line (--) and multi-line (/- ... -/) comments from a Lean proof string.
    
    This function correctly handles nested multi-line comments by keeping track of the
    nesting depth. It works for both multi-line string literals and single-line
    string literals containing newline characters (\\n).

    Args:
        lean_code: A string containing the Lean code.

    Returns:
        A new string with all comments removed.
    """
    
    # --- State Variables ---
    # nesting_level tracks the depth of nested multi-line comments.
    # A value of 0 means we are not inside a multi-line comment.
    nesting_level = 0
    # in_single_line_comment is a flag for single-line comments.
    in_single_line_comment = False
    
    # We build the output string in a list of characters for efficiency.
    result_parts = []
    
    # We use a manual index `i` to iterate through the string. This allows us
    # to look ahead two characters (e.g., for '/-' or '--') and skip ahead.
    i = 0
    n = len(lean_code)
    
    while i < n:
        # --- State: Inside a multi-line comment ---
        if nesting_level > 0:
            # Check for the start of a nested multi-line comment
            if lean_code[i:i+2] == '/-':
                nesting_level += 1
                i += 2
            # Check for the end of a multi-line comment
            elif lean_code[i:i+2] == '-/':
                nesting_level -= 1
                i += 2
            # Otherwise, this character is part of the comment, so we skip it
            else:
                i += 1
        
        # --- State: Inside a single-line comment ---
        elif in_single_line_comment:
            # A single-line comment ends at the next newline character
            if lean_code[i] == '\n':
                in_single_line_comment = False
                # It's important to preserve the newline to maintain line structure
                result_parts.append('\n')
            # Move to the next character
            i += 1
            
        # --- State: Not in any comment ---
        else:
            # Check for the start of a multi-line comment
            if lean_code[i:i+2] == '/-':
                nesting_level += 1
                i += 2
            # Check for the start of a single-line comment
            elif lean_code[i:i+2] == '--':
                in_single_line_comment = True
                i += 2
            # If not a comment, this character is part of the code
            else:
                result_parts.append(lean_code[i])
                i += 1
                
    # Join all the collected parts into the final, clean string
    return "".join(result_parts)

def split_proof_at_first_statement(proof):
    """
    Splits the proof string into two parts at the first appearance of 'axiom', 'lemma', or 'theorem'.
    Returns a tuple: (before, after), where 'after' starts with the matched keyword.
    """
    match = re.search(r'\b(axiom|lemma|theorem)\b', proof)
    if match:
        idx = match.start()
        logger.debug(f"proof is splitted into {proof[:idx]} and {proof[idx:]}")
        return proof[:idx], proof[idx:]
    else:
        logger.debug(f"{proof} is not splitted")
        return proof, ''  # No keyword found

def remove_imports_from_proof(proof):
	"""
	Remove all single-line import statements (lines starting with 'import') from a Lean proof.
	"""
	_, body = split_proof_at_first_statement(proof)
	return body.strip()

def remove_comments_and_axioms_from_proof(proof):
    """
    Remove all axiom blocks (which may span multiple lines) from a Lean proof.
    An axiom block ends with a blank line (\n\n).
    """
    # at this point, very "brute force" methods. find the first lemma and throw away
    # everything before
    proof = remove_lean_comments(proof).strip()
    #
    if 'lemma' in proof:
        proof_split = proof.split('lemma')
        proof = 'lemma' + 'lemma'.join(proof_split[1:])
        return proof.strip()
    else:
        # use theorem
        proof_split = proof.split('theorem')
        proof = 'theorem' + 'theorem'.join(proof_split[1:])
        return proof.strip()

def substitute_final_theorem(lean_proof: str, problem_statement: str) -> str:
    """
    Substitutes the final theorem signature in a Lean proof with the one from a
    given problem statement, while preserving the original proof block.

    This function finds the last occurrence of the keyword "theorem", replaces
    the signature (everything before ':=') with the signature from the problem
    statement, and keeps the original proof (everything after ':='). It correctly
    discards any 'import' or 'open' statements from the problem statement.

    Args:
        lean_proof: The string containing the full Lean proof.
        problem_statement: The string containing the new theorem signature, which
                           may end in ':= by sorry'.

    Returns:
        A new string with the final theorem signature replaced.
    """
    # --- 1. Normalize the input strings ---
    proof = lean_proof.strip()
    problem = problem_statement.strip()

    # --- 2. Find the start of the last theorem in the original proof ---
    last_theorem_index = proof.rfind('\ntheorem ')
    if last_theorem_index == -1 and proof.startswith('theorem '):
        last_theorem_index = 0

    # --- 3. If a theorem is found, perform the substitution ---
    if last_theorem_index != -1:
        # --- 3a. Isolate the parts of the original proof ---
        proof_prefix = proof[:last_theorem_index]
        final_theorem_block = proof[last_theorem_index:]
        
        proof_start_index = final_theorem_block.find(':=')
        if proof_start_index == -1:
            return proof_prefix.strip() + "\n\n" + problem

        original_proof_part = final_theorem_block[proof_start_index:]

        # --- 3b. Isolate ONLY the theorem signature from the problem statement ---
        # First, find the start of the theorem keyword to ignore imports/open
        problem_theorem_start_index = problem.rfind('\ntheorem ')
        if problem_theorem_start_index == -1 and problem.startswith('theorem '):
            problem_theorem_start_index = 0
        
        if problem_theorem_start_index == -1:
            # Fallback: No theorem found in problem statement
            return proof_prefix.strip() + "\n\n" + problem

        # Now find the end of the signature
        signature_end_index = problem.rfind(':=')
        if signature_end_index == -1:
            return proof_prefix.strip() + "\n\n" + problem

        # Extract just the theorem signature, excluding imports
        new_signature_part = problem[problem_theorem_start_index:signature_end_index]

        # --- 3c. Combine the parts to form the new proof ---
        return proof_prefix.strip() + "\n\n" + new_signature_part.strip() + " " + original_proof_part.strip()
    else:
        # Edge Case: If no "theorem" keyword is found, append the problem statement.
        return proof + "\n\n" + problem

def extract_open_line(header: str):
    """
    Returns the first line in the proof that starts with 'open' (ignoring leading whitespace).
    Returns None if no such line exists.
    """
    for line in header.splitlines():
        if line.strip().startswith('open'):
            return line
    return None

def process_import_part(header):
    line = extract_open_line(header)
    if not line:
        return DEFAULT_HEADER
    return DEFAULT_HEADER_NO_OPEN+line+'\n\n'

##############################################################
### Function to parse error message from lean code
##############################################################

# helper function to parse error str
def get_error_str(code, errors, error_thres):
    err_str = ""
    code_lines = code.split('\n')
    token_lengths = [len(line) + 1 for line in code_lines]
    
    error_num_thres = 8 if error_thres else len(errors)

    for i, error in enumerate(errors[:error_num_thres]):
        start_line = error['pos']['line'] - 1
        start_col = error['pos']['column']

        if error['endPos'] is None:
            end_line = start_line
            end_col = len(code_lines[start_line])
        else:
            end_line = error['endPos']['line'] - 1
            end_col = error['endPos']['column']

        start_char_pos = sum(token_lengths[:start_line]) + start_col
        end_char_pos = sum(token_lengths[:end_line]) + end_col
        
        err_str += f"\nError {i + 1}:\n"
        err_str += f"\nCorresponding Code:\n```lean4\n"
        
        error_code = ""
        for ii in range(-4, 0):
            if start_line + ii >= 0:
                error_code += f"{code_lines[start_line + ii]}\n"
        if start_line != end_line:
            error_code += code_lines[start_line][:start_col] + "<error>" + code_lines[start_line][start_col:] + "\n"
            
            if not error_thres:
                for j in range(start_line + 1, end_line):
                    error_code += f"{code_lines[j]}\n"
            else:
                show_line = 6
                for j in range(start_line + 1, min(end_line, start_line + show_line)):
                    error_code += f"{code_lines[j]}\n"
                if end_line > start_line + show_line:
                    leading_spaces = len(code_lines[j]) - len(code_lines[j].lstrip(' '))
                    error_code += "\n" + " " * leading_spaces + "... --[Truncated]-- ...\n"

            error_code += code_lines[end_line][:end_col] + "</error>" + code_lines[end_line][end_col:] + "\n"
        else:
            error_code += code_lines[start_line][:start_col] + "<error>" + code_lines[start_line][start_col:end_col] + "</error>" + code_lines[start_line][end_col:] + "\n"
        if end_line + 1 < len(code_lines):
            error_code += f"{code_lines[end_line + 1]}\n"
            
        err_str += error_code
        err_str += f"\n```\n"
        err_str += f"\nError Message: {error['data']}\n"
    
    if len(errors) > error_num_thres:
        err_str += f"\n... [Omitted {len(errors) - error_num_thres} more errors] ...\n"
        
    return err_str


class LightweightHandler(ABC):
    """
    Abstract base class for handling LLM input and output for lightweight search tasks.
    """
    @classmethod
    @abstractmethod
    def format_input(cls, *args, **kwargs):
        """Prepare the input for the LLM."""
        pass

    @classmethod
    @abstractmethod
    def process_output(cls, llm_output, *args, **kwargs):
        """Process the output from the LLM."""
        pass

class InferenceHandler(LightweightHandler):
    @classmethod
    def format_input(cls, statement, facts=None):
        # Example: format data for inference
        # if facts == None or (type(facts) == list and len(facts) == 0):
        if facts == None:
            # in this case, no proved facts
            return INFERENCE_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE.format(original_question_lean4=statement)
        elif type(facts) == list:
            axiom_str = '\n\n'.join(facts)
            return INFERENCE_AXIOMS_LEMMA_OUTPUT_TEMPLATE.format(axioms=axiom_str,original_question_lean4=statement)
        else:
            raise ValueError("Note implemented revision with proved facts.")

    @classmethod
    def process_output(cls, output, statement, facts=None):
        """
		Extract the last block wrapped by ```lean4 ... ``` from the output.
		If not found, return the original output.
		"""
        use_facts = False
        axioms_str = ''
        if type(facts) == list and len(facts) > 0:
            axioms_str = '\n\n'.join(facts)
            use_facts = True

        pattern = r"```lean4(.*?)```"
        pattern1 = r"```lean(.*?)```"
        matches = re.findall(pattern, output, re.DOTALL)
        imports_and_opens, statement_body = split_proof_at_first_statement(statement)
        if matches:
            return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(matches[-1].strip()))
            return_str = substitute_final_theorem(return_str, statement)
            return_str = return_str.strip()
            if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
                return statement
            if use_facts:
                return process_import_part(imports_and_opens) + '\n\n' + axioms_str + '\n\n' + return_str
            else:
                return process_import_part(imports_and_opens) + return_str
        matches1 = re.findall(pattern1, output, re.DOTALL)
        if matches1:
            return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(matches1[-1].strip()))
            return_str = substitute_final_theorem(return_str, statement)
            return_str = return_str.strip()
            if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
                return statement
            if use_facts:
                return process_import_part(imports_and_opens) + '\n\n' + axioms_str + '\n\n' + return_str
            else:
                return process_import_part(imports_and_opens) + return_str
        return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(output.strip()))
        return_str = substitute_final_theorem(return_str, statement)
        return_str = return_str.strip()
        if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
            return statement
        return process_import_part(imports_and_opens) + return_str

class RevisionHandler(LightweightHandler):
    @classmethod
    def format_input(cls, statement, previous_proof, errors, facts=None):
        # Example: format data for inference
        if facts == None or (type(facts) == list and len(facts) == 0):
            # in this case, no proved facts
            error_msgs = get_error_str(previous_proof,errors,True)
            return REVISION_NOAXIOMS_LEMMA_OUTPUT_TEMPLATE.format(original_question_lean4=statement, last_full_proof=previous_proof, error_message_for_prev_round=error_msgs)
        elif type(facts) == list:
            error_msgs = get_error_str(previous_proof,errors,True)
            axiom_str = '\n\n'.join(facts)
            return REVISION_AXIOMS_LEMMA_OUTPUT_TEMPLATE.format(axioms=axiom_str,original_question_lean4=statement, last_full_proof=previous_proof, error_message_for_prev_round=error_msgs)
        else:
            raise ValueError("Note implemented revision with proved facts.")

    @classmethod
    def process_output(cls, output, statement, facts=None):
        """
		Extract the last block wrapped by ```lean4 ... ``` from the output.
		If not found, return the original output.
		"""
        use_facts = False
        axioms_str = ''
        if type(facts) == list and len(facts) > 0:
            axioms_str = '\n\n'.join(facts)
            use_facts = True
        
        pattern = r"```lean4(.*?)```"
        pattern1 = r"```lean(.*?)```"
        matches = re.findall(pattern, output, re.DOTALL)
        imports_and_opens, statement_body = split_proof_at_first_statement(statement)
        if matches:
            return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(matches[-1].strip()))
            return_str = substitute_final_theorem(return_str, statement)
            return_str = return_str.strip()
            if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
                return statement
            if use_facts:
                return process_import_part(imports_and_opens) + '\n\n' + axioms_str + '\n\n' + return_str
            else:
                return process_import_part(imports_and_opens) + return_str
        matches1 = re.findall(pattern1, output, re.DOTALL)
        if matches1:
            return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(matches1[-1].strip()))
            return_str = substitute_final_theorem(return_str, statement)
            return_str = return_str.strip()
            if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
                return statement
            if use_facts:
                return process_import_part(imports_and_opens) + '\n\n' + axioms_str + '\n\n' + return_str
            else:
                return process_import_part(imports_and_opens) + return_str
        return_str = remove_imports_from_proof(remove_comments_and_axioms_from_proof(output.strip()))
        return_str = substitute_final_theorem(return_str, statement)
        return_str = return_str.strip()
        if 'apply?' in return_str or 'exact?' in return_str or 'admit' in return_str or 'axiom' in return_str:
            return statement
        return process_import_part(imports_and_opens) + return_str