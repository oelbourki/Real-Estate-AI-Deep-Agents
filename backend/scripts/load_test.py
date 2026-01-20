"""Load testing script."""
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def make_request(session: aiohttp.ClientSession, url: str, data: dict) -> Dict:
    """Make a single request and measure time."""
    start_time = time.time()
    try:
        async with session.post(url, json=data) as response:
            duration = time.time() - start_time
            return {
                "status": response.status,
                "duration": duration,
                "success": 200 <= response.status < 400
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "status": 0,
            "duration": duration,
            "success": False,
            "error": str(e)
        }


async def load_test(url: str, num_requests: int = 100, concurrency: int = 10):
    """
    Run load test.
    
    Args:
        url: API endpoint URL
        num_requests: Total number of requests
        concurrency: Number of concurrent requests
    """
    logger.info(f"Starting load test: {num_requests} requests, {concurrency} concurrent")
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request():
            async with semaphore:
                return await make_request(
                    session,
                    url,
                    {"message": "Test message", "user_name": "LoadTest"}
                )
        
        start_time = time.time()
        tasks = [bounded_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
    
    # Analyze results
    durations = [r["duration"] for r in results]
    successes = sum(1 for r in results if r["success"])
    errors = num_requests - successes
    
    print("\n" + "="*50)
    print("LOAD TEST RESULTS")
    print("="*50)
    print(f"Total Requests: {num_requests}")
    print(f"Concurrent: {concurrency}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Requests/sec: {num_requests/total_time:.2f}")
    print(f"Successes: {successes}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {successes/num_requests*100:.2f}%")
    print(f"\nResponse Times:")
    print(f"  Min: {min(durations):.3f}s")
    print(f"  Max: {max(durations):.3f}s")
    print(f"  Mean: {statistics.mean(durations):.3f}s")
    print(f"  Median: {statistics.median(durations):.3f}s")
    if len(durations) > 1:
        print(f"  Std Dev: {statistics.stdev(durations):.3f}s")
    print("="*50)


if __name__ == "__main__":
    import sys
    
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1/chat"
    num_requests = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    asyncio.run(load_test(url, num_requests, concurrency))
