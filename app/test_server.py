"""
Test server for E2E testing using new structure.
"""
import os
from flask import Flask, request, jsonify
from core import DocumentProcessor, RAGService
from config import config

app = Flask(__name__)


@app.route("/test", methods=["POST"])
def e2e_test():
    """Handle E2E test requests."""
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query not provided"}), 400

    try:
        # Get test configuration
        temperature = float(os.getenv("TEST_TEMPERATURE", str(config.default_temperature)))
        top_k = int(os.getenv("TEST_TOP_K", str(config.default_top_k)))
        chunk_size = int(os.getenv("TEST_CHUNK_SIZE", str(config.default_chunk_size)))
        chunk_overlap = int(os.getenv("TEST_CHUNK_OVERLAP", str(config.default_chunk_overlap)))
        model_name = os.getenv("TEST_MODEL_NAME", config.ollama_model_name)

        # Load documents
        processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        documents = processor.load_documents(config.data_dir)

        if not documents:
            return jsonify({"error": "No documents loaded"}), 500

        # Initialize RAG
        rag_service = RAGService(
            embedding_model=config.embedding_model,
            ollama_host=config.ollama_host,
            model_name=model_name,
            temperature=temperature,
            top_k=top_k,
            timeout=config.llm_timeout
        )

        rag_chain = rag_service.initialize(documents)
        if not rag_chain:
            return jsonify({"error": "RAG chain not initialized"}), 500

        # Process query
        response = rag_service.query(query)
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8599)
