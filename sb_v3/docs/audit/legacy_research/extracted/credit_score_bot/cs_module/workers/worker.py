import asyncio

class BaseWorker:
    def __init__(self, worker_id, job_queue, result_queue):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.result_queue = result_queue

    async def run(self):
        while True:
            job = await self.job_queue.get()
            if job is None: # Sentinel for stopping
                break
            try:
                result = await self.process_job(job)
                await self.result_queue.put(result)
            except Exception as e:
                await self.result_queue.put({"error": str(e), "job": job})
            finally:
                self.job_queue.task_done()

    async def process_job(self, job):
        raise NotImplementedError("Subclasses must implement process_job")
