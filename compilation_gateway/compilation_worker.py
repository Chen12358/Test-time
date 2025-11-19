# compilation_worker.py

import os
import asyncio
import uvicorn
import httpx
import logging
import multiprocessing as mp # Import multiprocessing here
from fastapi import FastAPI, Request, HTTPException
from typing import List, Dict

from multiprocess_compiler_pool_shange import MultiProcessCompilerPool

# --- THE DEFINITIVE FIX - PART 1 ---
# Set the start method to 'spawn' for compatibility with asyncio/uvicorn.
# This MUST be done at the top level of the main script.
mp.set_start_method('spawn', force=True)
# ------------------------------------

# --- Configuration ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables for SLURM ---
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8001")
NUM_PROCESSES = int(os.getenv("SLURM_CPUS_PER_TASK", os.cpu_count()))
LAKE_PATH = os.getenv("LAKE_PATH", f'{os.path.expanduser("~")}/.elan/bin/lake')
LEAN_WORKSPACE = os.getenv("LEAN_WORKSPACE", '/path/to/your/mathlib4') # IMPORTANT: Set this

app = FastAPI(title="Lean Compilation Worker")

# Moniter queue size
async def monitor_queue(interval_seconds: int = 5):
    """Periodically logs the size of the compilation queue."""
    while True:
        try:
            # The compiler pool is attached to the app's state
            if hasattr(app.state, 'compiler_pool'):
                pool: MultiProcessCompilerPool = app.state.compiler_pool
                
                # We will add this get_queue_size() method in the next step
                queue_size = pool.get_queue_size()
                logger.info(f"Compilation queue length: {queue_size}")
            else:
                logger.info("Compiler pool not initialized yet, skipping queue check.")
                
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}", exc_info=True)
            
        await asyncio.sleep(interval_seconds)

# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting multiprocessing pool with {NUM_PROCESSES} child processes (using 'spawn' method)...")
    
    compiler_pool = MultiProcessCompilerPool(
        num_workers=NUM_PROCESSES,
        lake_path=LAKE_PATH,
        lean_workspace=LEAN_WORKSPACE
    )
    compiler_pool.start_workers()
    app.state.compiler_pool = compiler_pool
    
    logger.info("Multiprocessing pool started.")
    asyncio.create_task(register_with_gateway())
    # launch the monitoring task
    asyncio.create_task(monitor_queue())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down multiprocessing pool...")
    app.state.compiler_pool.shutdown()

async def register_with_gateway():
    registration_payload = {"url": WORKER_URL}
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{GATEWAY_URL}/register", json=registration_payload, timeout=5)
            logger.info(f"Successfully registered with gateway at {GATEWAY_URL}")
            return
        except httpx.RequestError:
            logger.warning(f"Could not register with gateway. Retrying in 5 seconds...")
            await asyncio.sleep(5)

# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/compile", response_model=List[Dict])
async def compile_batch(tasks: List[Dict], request: Request):
    print(f"Received batch of {len(tasks)} compilation tasks.")
    pool: MultiProcessCompilerPool = request.app.state.compiler_pool
    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(None, pool.run_batch, tasks)
        return results
    except Exception as e:
        logger.error(f"Error in batch compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process compilation batch.")

@app.post("/compile_one", response_model=Dict)
async def compile_one(task: Dict, request: Request):
    print(f"Received single compilation task.")
    pool: MultiProcessCompilerPool = request.app.state.compiler_pool
    loop = asyncio.get_running_loop()
    try:
        results_list = await loop.run_in_executor(None, pool.run_batch, [task])
        print(f"Single task compilation result: {results_list}")
        if not results_list:
            raise HTTPException(status_code=500, detail="Compilation returned no result.")
        return results_list[0]
    except Exception as e:
        logger.error(f"Error in single compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process single compilation task.")

if __name__ == "__main__":
    port = int(WORKER_URL.split(":")[-1])
    uvicorn.run(app, host="0.0.0.0", port=port)