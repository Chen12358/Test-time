# multiprocess_compiler_pool.py

import os
import time
import json
import pexpect
import multiprocessing as mp
import uuid
from typing import List, Dict, Any
import logging

import tempfile
import subprocess
import traceback

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_IMPORTS = (
    "import Mathlib\n"
    "import Aesop\n"
)

DEFAULT_HEADER = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat Polynomial Complex\n\n"

# --- Helper Functions ---

def split_import_and_body(code: str):
    lines = code.splitlines()
    import_lines = [line.strip() for line in lines if line.strip().startswith("import")]
    body_lines = [line for line in lines if not line.strip().startswith("import")]
    lean_body = "\n".join(body_lines)
    
    # If no imports are found, use the default ones.
    if not import_lines:
        import_block = DEFAULT_IMPORTS.strip()
    else:
        import_block = "\n".join(import_lines)
        
    return import_block, lean_body

def split_import_and_body(code: str, default_imports=DEFAULT_IMPORTS):
    """
    Split Lean code into (import_block, lean_body), treating only lines that begin with 'import'
    as part of the import block. Moves trailing blank lines after the import block into the body.
    Canonicalizes to DEFAULT_IMPORTS if all import lines are contained in it.
    """
    lines = code.splitlines()
    import_lines = []
    body_lines = []

    last_import_idx = -1
    saw_import = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import"):
            saw_import = True
            import_lines.append(stripped)
            last_import_idx = len(import_lines) - 1
        elif saw_import:
            body_lines = lines[i:]
            break
        else:
            body_lines.append(line)

    # Move trailing blank lines from import block to body
    if saw_import and last_import_idx + 1 < len(import_lines):
        trailing_blank_lines = import_lines[last_import_idx + 1:]
        import_lines = import_lines[:last_import_idx + 1]
        body_lines = trailing_blank_lines + body_lines

    import_block = "\n".join(import_lines)
    lean_body = "\n".join(body_lines)

    # Normalize to DEFAULT_IMPORTS if all imports are contained in it
    default_import_lines = set(line.strip() for line in default_imports.strip().splitlines() if line.strip().startswith("import"))
    actual_import_lines = set(import_lines)

    if actual_import_lines.issubset(default_import_lines):
        return default_imports.strip(), lean_body

    return import_block.strip(), lean_body

# def initiate_child(config: dict):
#     # This REPL will now be a long-running process that holds modules in memory.
#     child = pexpect.spawn(
#         "/bin/bash", 
#         args=['-l'], 
#         cwd=config["lean_workspace"], 
#         encoding='utf-8', 
#         maxread=1, 
#         echo=False
#     )
#     child.sendline("stty -icanon")
#     child.sendline(f'{config["lake_path"]} exe repl')
#     # We send an initial, simple command just to make sure it's ready.
#     send_command_and_wait(child, DEFAULT_IMPORTS, timeout=config["import_timeout"], config=config)
#     return child

# def send_command_and_wait(child, command, timeout, config):
#     json_cmd = json.dumps({"cmd": command}, ensure_ascii=False)
#     child.sendline(json_cmd)
#     child.sendline("")
#     try:
#         child.expect(["\r\n\r\n", "\n\n"], timeout=timeout)
#         block = child.before.strip()
#         result = json.loads(block)
#         errors = [m for m in result.get("messages", []) if m.get("severity") == "error"]
#         parsed_result = {
#             "errors": errors, "sorries": result.get("sorries", []), "system_errors": None,
#             "pass": not errors, "complete": (not errors) and (not result.get("sorries", []))
#         }
#     except json.JSONDecodeError as e:
#         parsed_result = {"pass": False, "complete": False, "system_errors": f"JSONDECODE ERROR: {e}"}
#     except (pexpect.TIMEOUT, pexpect.EOF) as e:
#         parsed_result = {"pass": False, "complete": False, "system_errors": f"PEXPECT ERROR: {e}"}
#     return {"code": command, "compilation_result": parsed_result}


def verify_lean4_file(command, config):
    message_str = json.dumps({"cmd": command}, ensure_ascii=False)
    system_messages = ''
    try:
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as temp_file:
            temp_file.write(message_str + "\r\n\r\n")
            temp_file.seek(0)


            outputs = subprocess.run([config["lake_path"], "exe", 'repl'], stdin=temp_file, capture_output=True, text=True, cwd=config["lean_workspace"], timeout=config["import_timeout"]+config["proof_timeout"])
        result = json.loads(outputs.stdout)

        errors = [m for m in result.get("messages", []) if m.get("severity") == "error"]
        result = {
            "errors": errors, "sorries": result.get("sorries", []), "system_errors": None,
            "pass": not errors, "complete": (not errors) and (not result.get("sorries", []))
        }
    except:
        result = {
            "pass": False,
            "complete": False,
            "system_errors": traceback.format_exc(),
            "system_messages": system_messages
        }
    return result



def worker(worker_id, task_queue, result_list, total_restarts, lock, config):
    
    while True:
        indexed_task = task_queue.get()
        if indexed_task is None: break
        
        task_payload = indexed_task["payload"]
        import_block, lean_body = split_import_and_body(task_payload["code"])
        
        # ** THE FIX **
        # Always prepend the import block to the body for each command.
        # Lean's importer is fast if the modules are already in memory.
        # This ensures the context is always correct.
        #full_command = import_block + "\n\n" + lean_body
        #full_command = DEFAULT_HEADER + "\n\n" + lean_body
        full_command = task_payload["code"]
        
        response = verify_lean4_file(full_command, config=config)

        final_response = {}

        final_response.update(task_payload)
        final_response["compilation_result"] = response

        
        # response.update(task_payload)
        # response["code"] = task_payload["code"] # Return the original code
        # response["header"] = import_block
        # response["index"] = indexed_task["index"]
        # response["batch_id"] = indexed_task["batch_id"]

        final_response["code"] = task_payload["code"] # Return the original code
        final_response["header"] = import_block
        final_response["index"] = indexed_task["index"]
        final_response["batch_id"] = indexed_task["batch_id"]

        # with lock: result_list.append(response)
        with lock: result_list.append(final_response) 

class MultiProcessCompilerPool:
    def __init__(self, num_workers: int, lake_path: str, lean_workspace: str):
        self.num_workers, self.lake_path, self.lean_workspace = num_workers, lake_path, lean_workspace
        self.import_timeout, self.proof_timeout = 100, 200
        self.task_queue, manager = mp.Queue(), mp.Manager()
        self.result_list, self.lock, self.total_restarts = manager.list(), manager.Lock(), mp.Value('i', 0)
        self.workers: List[mp.Process] = []

    def start_workers(self):
        config = {
            "lean_workspace": self.lean_workspace, "lake_path": self.lake_path,
            "import_timeout": self.import_timeout, "proof_timeout": self.proof_timeout,
        }
        for i in range(self.num_workers):
            p = mp.Process(target=worker, args=(i, self.task_queue, self.result_list, self.total_restarts, self.lock, config))
            p.start()
            self.workers.append(p)
        logger.info(f"Spawned {self.num_workers} child compiler processes.")

    def run_batch(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tasks: return []
        batch_id, num_tasks = str(uuid.uuid4()), len(tasks)
        for i, task in enumerate(tasks):
            self.task_queue.put({"payload": task, "index": i, "batch_id": batch_id})
        collected_results = []
        while len(collected_results) < num_tasks:
            time.sleep(0.05)
            with self.lock:
                results_for_batch = [r for r in self.result_list if r.get("batch_id") == batch_id]
                if len(results_for_batch) >= num_tasks:
                    collected_results = results_for_batch
                    remaining = [r for r in self.result_list if r.get("batch_id") != batch_id]
                    self.result_list[:] = remaining
        sorted_results = sorted(collected_results, key=lambda r: r["index"])
        for res in sorted_results: res.pop("index", None); res.pop("batch_id", None)
        return sorted_results
    
    def get_queue_size(self) -> int:
        """Returns the approximate size of the task queue."""
        return self.task_queue.qsize()

    def shutdown(self):
        for _ in range(self.num_workers): self.task_queue.put(None)
        for p in self.workers:
            p.join(timeout=5)
            if p.is_alive(): p.terminate()