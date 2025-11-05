"""Request queue service for managing concurrent RAG requests."""
import time
import logging
from datetime import datetime
from queue import Queue, Empty
from threading import Thread, Lock
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RequestQueue:
    """Manages a queue of RAG requests with limited concurrency."""

    def __init__(self, max_concurrent: int = 1):
        """
        Initialize request queue.

        Args:
            max_concurrent: Maximum number of concurrent requests to process
        """
        self.queue = Queue()
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.completed_requests: Dict[str, Dict[str, Any]] = {}
        self.max_concurrent = max_concurrent
        self.current_processing = 0
        self.lock = Lock()
        self.worker_thread: Optional[Thread] = None
        self.start_worker()

    def start_worker(self) -> None:
        """Start the background worker thread."""
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.worker_thread = Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("Request queue worker started")

    def add_request(self, request_id: str, query: str, rag_chain) -> str:
        """
        Add a request to the queue.

        Args:
            request_id: Unique request identifier
            query: User query
            rag_chain: RAG chain to use for processing

        Returns:
            Request ID
        """
        data = {
            'id': request_id,
            'query': query,
            'rag_chain': rag_chain,
            'timestamp': datetime.now(),
            'status': 'queued'
        }
        with self.lock:
            self.active_requests[request_id] = data
            self.queue.put(data)

        logger.info(f"Request {request_id} added to queue")
        return request_id

    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a request.

        Args:
            request_id: Request identifier

        Returns:
            Request data dictionary or None if not found
        """
        with self.lock:
            return self.completed_requests.get(request_id) or \
                   self.active_requests.get(request_id)

    def get_queue_position(self, request_id: str) -> int:
        """
        Get position of request in queue.

        Args:
            request_id: Request identifier

        Returns:
            Queue position (0 if processing, -1 if not found)
        """
        with self.lock:
            if request_id not in self.active_requests:
                return -1

            status = self.active_requests[request_id]['status']
            if status == 'processing':
                return 0

            if status == 'queued':
                queue_items = list(self.queue.queue)
                for i, req in enumerate(queue_items):
                    if req['id'] == request_id:
                        return i + self.current_processing

        return -1

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue stats
        """
        with self.lock:
            return {
                'queue_size': self.queue.qsize(),
                'active_count': len(self.active_requests),
                'processing_count': self.current_processing,
                'max_concurrent': self.max_concurrent
            }

    def _process_queue(self) -> None:
        """Background worker that processes queued requests."""
        while True:
            try:
                if self.current_processing < self.max_concurrent:
                    req = self.queue.get(timeout=1)
                    Thread(
                        target=self._execute_rag_request,
                        args=(req,),
                        daemon=True
                    ).start()
                else:
                    time.sleep(0.1)
            except Empty:
                time.sleep(0.5)

    def _execute_rag_request(self, req: Dict[str, Any]) -> None:
        """
        Execute a single RAG request.

        Args:
            req: Request data dictionary
        """
        with self.lock:
            self.current_processing += 1
            req['status'] = 'processing'
            req['start_time'] = datetime.now()

        logger.info(f"Processing request {req['id']}: {req['query']}")

        try:
            resp = req['rag_chain'].invoke({"input": req['query']})

            with self.lock:
                req['status'] = 'completed'
                req['response'] = resp
                req['end_time'] = datetime.now()
                self.completed_requests[req['id']] = req
                self.active_requests.pop(req['id'], None)

            logger.info(f"✅ Request {req['id']} completed successfully")

        except Exception as e:
            with self.lock:
                req['status'] = 'error'
                req['error'] = str(e)
                self.completed_requests[req['id']] = req
                self.active_requests.pop(req['id'], None)

            logger.error(f"❌ Request {req['id']} failed: {str(e)}")

        finally:
            with self.lock:
                self.current_processing -= 1
            self.queue.task_done()
