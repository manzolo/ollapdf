"""Unit tests for RequestQueue."""
import pytest
import time
from services.request_queue import RequestQueue


class TestRequestQueue:
    """Tests for RequestQueue class."""

    def test_init(self):
        """Test queue initialization."""
        queue = RequestQueue(max_concurrent=2)
        assert queue.max_concurrent == 2
        assert queue.current_processing == 0
        assert len(queue.active_requests) == 0
        assert len(queue.completed_requests) == 0

    def test_get_queue_stats(self):
        """Test getting queue statistics."""
        queue = RequestQueue(max_concurrent=1)
        stats = queue.get_queue_stats()
        assert 'queue_size' in stats
        assert 'active_count' in stats
        assert 'processing_count' in stats
        assert 'max_concurrent' in stats
        assert stats['max_concurrent'] == 1

    def test_get_request_status_not_found(self):
        """Test getting status of non-existent request."""
        queue = RequestQueue()
        status = queue.get_request_status("nonexistent_id")
        assert status is None

    def test_get_queue_position_not_found(self):
        """Test getting position of non-existent request."""
        queue = RequestQueue()
        position = queue.get_queue_position("nonexistent_id")
        assert position == -1


class TestRequestQueueIntegration:
    """Integration tests for RequestQueue."""

    @pytest.mark.slow
    def test_add_and_process_request(self, mock_documents):
        """Test adding and processing a simple request."""
        queue = RequestQueue(max_concurrent=1)

        # Create a mock RAG chain
        class MockRAGChain:
            def invoke(self, input_dict):
                return {"answer": f"Response to: {input_dict['input']}", "context": []}

        mock_chain = MockRAGChain()
        request_id = queue.add_request("test_1", "Test query", mock_chain)

        assert request_id == "test_1"

        # Wait for processing
        max_wait = 5  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status = queue.get_request_status(request_id)
            if status and status['status'] == 'completed':
                break
            time.sleep(0.1)

        # Check results
        status = queue.get_request_status(request_id)
        assert status is not None
        assert status['status'] == 'completed'
        assert 'response' in status
        assert status['response']['answer'] == "Response to: Test query"
