import os
import asyncio
import uvicorn
import httpx
import logging
import multiprocessing as mp
from fastapi import FastAPI, Request, HTTPException
from typing import List, Dict

# Assuming 'multiprocess_compiler_pool.py' is in the same directory
from multiprocess_compiler_pool_shange import MultiProcessCompilerPool

# --- THE DEFINITIVE FIX - PART 1 ---
# Set the start method to 'spawn' for compatibility with asyncio/uvicorn.
# This MUST be done at the top level of the main script.

mp.set_start_method('spawn', force=True)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8001")
NUM_PROCESSES = int(os.getenv("SLURM_CPUS_PER_TASK", os.cpu_count()))
LAKE_PATH = os.getenv("LAKE_PATH", f'{os.path.expanduser("~")}/.elan/bin/lake')
LEAN_WORKSPACE = os.getenv("LEAN_WORKSPACE", '/path/to/your/mathlib4') # IMPORTANT: Set this
RESTART_TOKEN = os.getenv("RESTART_TOKEN", "your-secret-token-here") # For manual restart

app = FastAPI(title="Lean Compilation Worker")

# --- Global Lock ---
# This lock protects the compiler pool.
# - /compile endpoints must acquire it to *use* the pool.
# - /restart logic must acquire it to *replace* the pool.
POOL_LOCK = asyncio.Lock()


# --- Helper Function for Pool Creation ---

def _create_and_start_pool():
    """
    A blocking helper function to initialize and start a new pool.
    This is run in an executor.
    """
    logger.info(f"Creating new compiler pool with {NUM_PROCESSES} workers...")
    new_pool = MultiProcessCompilerPool(
        num_workers=NUM_PROCESSES,
        lake_path=LAKE_PATH,
        lean_workspace=LEAN_WORKSPACE
    )
    new_pool.start_workers()
    logger.info("New pool started successfully.")
    return new_pool

# --- Core Restart Logic ---

async def _perform_pool_restart(app: FastAPI):
    """
    Safely shuts down the old pool and starts a new one.
    This is the core logic used by the API endpoint and the periodic task.
    """
    logger.warning("POOL RESTART: Process starting...")
    
    lock: asyncio.Lock = app.state.pool_lock
    loop = asyncio.get_running_loop()

    # 1. Acquire the lock. This blocks all new /compile jobs
    #    and waits for any existing ones to finish.
    await lock.acquire()
    logger.info("POOL RESTART: Lock acquired. No new jobs will be accepted.")
    
    try:
        # 2. Get the old pool and shut it down in an executor
        old_pool: MultiProcessCompilerPool = app.state.compiler_pool
        logger.warning("POOL RESTART: Shutting down old pool...")
        await loop.run_in_executor(None, old_pool.shutdown)
        logger.warning("POOL RESTART: Old pool shut down.")

        # 3. Create and start the new pool in an executor
        new_pool = await loop.run_in_executor(None, _create_and_start_pool)
        
        # 4. Hot-swap the pool in the app state
        app.state.compiler_pool = new_pool
        
    except Exception as e:
        logger.error(f"POOL RESTART: Failed: {e}", exc_info=True)
        # We must release the lock even if we fail!
        lock.release()
        logger.error("POOL RESTART: Lock released after failure.")
        raise  # Re-raise the exception
    
    # 5. Release the lock, allowing /compile jobs to use the new pool
    lock.release()
    logger.warning("POOL RESTART: Pool restart successful. Lock released.")


# --- Background Tasks ---

async def monitor_queue(interval_seconds: int = 60):
    """Periodically logs the size of the compilation queue."""
    while True:
        await asyncio.sleep(interval_seconds)
        
        if not hasattr(app.state, 'compiler_pool') or not hasattr(app.state, 'pool_lock'):
            logger.info("Compiler pool or lock not initialized yet, skipping queue check.")
            continue
        
        lock: asyncio.Lock = app.state.pool_lock
        
        #
        # The 'if lock.locked():' check has been REMOVED.
        #
        
        # This 'async with' block will now *wait* if the lock is busy.
        # Once it's free, it will acquire the lock, run the code,
        # and then release it.
        async with lock:
            try:
                # We can safely access the pool because we hold the lock
                pool: MultiProcessCompilerPool = app.state.compiler_pool
                queue_size = pool.get_queue_size()
                logger.info(f"Compilation queue length: {queue_size}")
            except Exception as e:
                logger.error(f"Error in monitoring task: {e}", exc_info=True)


async def register_with_gateway():
    """Registers this worker with the gateway upon startup."""
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

async def periodic_restarter(app: FastAPI, interval_minutes: int = 3):
    """
    Runs in the background, restarting the pool every 30 minutes.
    """
    logger.info(f"Pool restarter initiated. Will run every {interval_minutes} minutes.")
    while True:
        await asyncio.sleep(interval_minutes * 60) 
        
        logger.warning(f"PERIODIC RESTART: Triggering scheduled {interval_minutes}-minute pool restart...")
        try:
            await _perform_pool_restart(app)
        except Exception as e:
            # Log the error but don't stop the loop
            logger.error(f"PERIODIC RESTART: Scheduled restart failed, will retry in {interval_minutes} minutes. Error: {e}", exc_info=True)


# --- Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting worker and initial compiler pool...")
    
    # Run the blocking pool creation in an executor
    loop = asyncio.get_running_loop()
    compiler_pool = await loop.run_in_executor(None, _create_and_start_pool)
    
    # Store the pool and the lock in the app's state
    app.state.compiler_pool = compiler_pool
    app.state.pool_lock = POOL_LOCK
    
    logger.info("Multiprocessing pool started and lock initialized.")
    
    # Launch all background tasks
    asyncio.create_task(register_with_gateway())
    asyncio.create_task(monitor_queue())
    asyncio.create_task(periodic_restarter(app, interval_minutes=3))

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down worker...")
    if hasattr(app.state, 'compiler_pool'):
        logger.info("Shutting down multiprocessing pool...")
        # Run the blocking shutdown in an executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, app.state.compiler_pool.shutdown)
        logger.info("Pool shutdown complete.")
    logger.info("Worker shutdown complete.")

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    """Health check for the load balancer."""
    return {"status": "ok"}

@app.post("/compile", response_model=List[Dict])
async def compile_batch(tasks: List[Dict], request: Request):
    logger.info(f"Received batch of {len(tasks)} compilation tasks.")
    lock: asyncio.Lock = request.app.state.pool_lock

    # This 'async with' statement acquires the lock.
    # If the pool is restarting, this will wait until it's finished.
    async with lock:
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
    logger.info(f"Received single compilation task.")
    lock: asyncio.Lock = request.app.state.pool_lock

    # This 'async with' statement acquires the lock.
    async with lock:
        pool: MultiProcessCompilerPool = request.app.state.compiler_pool
        loop = asyncio.get_running_loop()
        try:
            results_list = await loop.run_in_executor(None, pool.run_batch, [task])
            if not results_list:
                raise HTTPException(status_code=500, detail="Compilation returned no result.")
            return results_list[0]
        except Exception as e:
            logger.error(f"Error in single compilation: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to process single compilation task.")

@app.post("/restart_pool")
async def restart_pool_endpoint(request: Request, token: str):
    """
    Manually trigger a pool restart.
    """
    if token != RESTART_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token.")
    
    try:
        # Call the same core logic function
        await _perform_pool_restart(request.app)
        return {"status": "pool_restarted"}
    except Exception as e:
        logger.error(f"Manual pool restart failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to restart pool: {e}")


# --- Main Execution ---

if __name__ == "__main__":
    # Friendly warning if the default path is used
    if LEAN_WORKSPACE == '/path/to/your/mathlib4':
        logger.warning("="*50)
        logger.warning("WARNING: LEAN_WORKSPACE is set to the default placeholder.")
        logger.warning("Please set the LEAN_WORKSPACE environment variable.")
        logger.warning("="*50)

    port = int(WORKER_URL.split(":")[-1])
    logger.info(f"Starting worker server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)