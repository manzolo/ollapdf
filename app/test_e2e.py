import requests
import time
import os

def test_e2e():
    """
    End-to-end test for the RAG system.
    """
    # Wait for the services to be ready
    time.sleep(60)

    test_query = "Hello, can you summarize the documents?"
    response = requests.post("http://e2e-test-server:8599/test", json={"query": test_query})

    assert response.status_code == 200
    response_data = response.json()
    assert "answer" in response_data
    assert "context" in response_data
    assert len(response_data["context"]) > 0

if __name__ == "__main__":
    test_e2e()
