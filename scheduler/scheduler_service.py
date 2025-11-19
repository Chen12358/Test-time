# scheduler_service.py

import asyncio
import logging
import httpx
from typing import Union, List, Dict, Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- Basic Configuration ---
logger = logging.getLogger(__name__)

# --- Priority Definitions ---
P_REVISION = 0
P_SUBPROBLEM = 1
P_INITIAL = 2

class InferenceSchedulerService:
    def __init__(self, vllm_gateway_url: str, num_workers: int = 200, timeout: int = 900):
        self._queue = asyncio.PriorityQueue()
        # Use httpx.AsyncClient for direct HTTP communication
        
        # Configure connection limits to match the number of workers
        limits = httpx.Limits(max_connections=num_workers, max_keepalive_connections=50)
        
        # Use httpx.AsyncClient for direct HTTP communication
        self._client = httpx.AsyncClient(base_url=vllm_gateway_url, timeout=timeout, limits=limits)
        self._num_workers = num_workers
        self._workers = []
        self._task_counter = 0

    @retry(
        stop=stop_after_attempt(0), # Try a maximum of 1 time (plus the initial attempt)
        wait=wait_exponential(multiplier=1, min=2, max=10), # Wait 2s, then 4s
        retry=retry_if_exception_type(httpx.RequestError) # Only retry on network errors
    )
    async def _make_api_call(self, prompt: Union[str, List[str]], model: str, extra_params: dict = None) -> Dict[str, Any]:
        """This is the function that will be retried on failure."""
        logger.debug(f"Attempting to get completion for prompt: {prompt[:30] if isinstance(prompt, str) else 'messages'}...")
        
        # The endpoint for OpenAI-compatible APIs is typically /v1/chat/completions
        target_url = "/v1/chat/completions"

        # support the input prompt with list (messages)
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            # if it is given as a list, then assume that it is wrapped in messages, e.g. the following
            # [{"role": "system", "content": xxx}, {"role": "user", "content": prompt}, {"role": "assistant", "content": res}]
            messages = prompt
        else:
            raise ValueError("Invalid prompt format")

        # Construct the JSON payload in the OpenAI API format
        payload = {
            "model": model,
            "messages": messages
        }
        if extra_params:
            payload.update(extra_params)
            
        # Make the POST request
        response = await self._client.post(target_url, json=payload)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        
        # Parse the JSON response to get the content and usage
        result = response.json()
        
        # Extract content and usage information
        content = result['choices'][0]['message']['content']
        usage = result.get('usage', {})
        
        return {
            'content': content,
            'usage': {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
        }

    async def _worker(self, name: str):
        """The worker task that processes items from the queue."""
        while True:
            priority, count, task_data, future = await self._queue.get()
            
            try:
                result = await self._make_api_call(
                    prompt=task_data["prompt"],
                    model=task_data["model"],
                    extra_params=task_data.get("extra_params", None)
                )
                if not future.done():
                    future.set_result(result)
                else:
                    logger.warning(f"Task succeeded, but its future was already resolved. Discarding result.")
            except Exception as e:
                # If all retries fail, set the exception on the future
                logging.error(f"Task failed after multiple retries: {e}")
                if not future.done():
                    future.set_exception(e)
            finally:
                self._queue.task_done()

    async def inference(self, prompt: Union[str, List[str]], model: str, priority: int = 10, extra_params: dict = None) -> Dict[str, Any]:
        """
        This is the INTERNAL API that other modules call.
        It returns a dictionary containing both the content and usage information.
        
        Returns:
            Dict with keys:
                - 'content': The generated text
                - 'usage': Dict with 'prompt_tokens', 'completion_tokens', 'total_tokens'
        """
        future = asyncio.Future()
        await self._queue.put((priority, self._task_counter, {"prompt": prompt, "model": model, "extra_params": extra_params}, future))
        self._task_counter += 1
        return await future

    def start(self):
        """Starts the worker pool."""
        for i in range(self._num_workers):
            task = asyncio.create_task(self._worker(f"Worker-{i}"))
            self._workers.append(task)
        print(f"{self._num_workers} workers started.")

    def stop(self):
        """Stops the workers."""
        for task in self._workers:
            task.cancel()
        print("Workers stopped.")

class CompilationSchedulerService:
    def __init__(self, compilation_gateway_url: str, num_workers: int = 200):
        """
        Initializes the scheduler for the Lean compilation service.

        Args:
            compilation_gateway_url (str): The base URL of the compilation gateway.
            num_workers (int): The maximum number of concurrent compilation requests.
        """
        # A simple FIFO queue is sufficient for now. Can be upgraded to PriorityQueue if needed.
        self._queue = asyncio.Queue()
        self._client = httpx.AsyncClient(timeout=400.0) # Use a long default timeout for compilation
        self._gateway_url = compilation_gateway_url
        self._workers = []

        # Start the worker tasks
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"Compiler-Worker-{i}"))
            self._workers.append(task)
        logger.info(f"Started {num_workers} compilation workers.")

    @retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Only retry on network errors, not on HTTP errors (like 4xx or 5xx)
        # or compilation failures, which are not transient.
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def _make_api_call(self, task_data: dict):
        """Makes the API call to the compilation gateway."""
        target_url = f"{self._gateway_url}/api/v1/compile_one"
        logger.debug(f"Submitting '{task_data.get('name')}' for compilation.")
        
        response = await self._client.post(target_url, json=task_data)
        response.raise_for_status() # Raise an exception for non-2xx status codes
        return response.json()

    async def _worker(self, name: str):
        """The worker task that processes items from the queue."""
        while True:
            task_data, future = await self._queue.get()
            
            try:
                result = await self._make_api_call(task_data)
                if not future.done():
                    future.set_result(result)
                else:
                    logger.warning(f"Task succeeded, but its future was already resolved. Discarding result.")
            except Exception as e:
                logger.error(f"Compilation for task '{task_data.get('name')}' failed after retries: {e}")
                if not future.done():
                    future.set_exception(e)
            finally:
                self._queue.task_done()

    async def compile(self, name: str, code: str):
        """
        Public API to submit a piece of Lean code for compilation.

        Returns:
            A future that will resolve with the compilation result dictionary.
        """
        future = asyncio.Future()
        task_data = {"name": name, "code": code}
        await self._queue.put((task_data, future))
        return await future

    def stop(self):
        """Stops the worker tasks."""
        for task in self._workers:
            task.cancel()
        logger.info("Compilation workers stopped.")