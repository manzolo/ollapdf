import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from utils import test_rag_system

if __name__ == "__main__":
    DATA_DIR = "data"
    print("Running RAG system test...")
    try:
        test_rag_system(DATA_DIR)
        print("RAG system test passed!")
    except Exception as e:
        print(f"RAG system test failed: {e}")
        sys.exit(1)
