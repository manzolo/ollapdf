"""
Test script for RAG system using new structure.
Run this to test the complete RAG pipeline.
"""
import sys
import logging
from core import DocumentProcessor, RAGService
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_rag_system():
    """Test the RAG system end-to-end."""
    logger.info("🧪 Starting RAG system test")

    try:
        # Load documents
        processor = DocumentProcessor(
            chunk_size=config.default_chunk_size,
            chunk_overlap=config.default_chunk_overlap
        )
        documents = processor.load_documents(config.data_dir)

        if not documents:
            logger.error("No documents loaded")
            return False

        # Initialize RAG service
        rag_service = RAGService(
            embedding_model=config.embedding_model,
            ollama_host=config.ollama_host,
            model_name=config.ollama_model_name,
            temperature=config.default_temperature,
            top_k=config.default_top_k,
            timeout=config.llm_timeout
        )

        rag_chain = rag_service.initialize(documents)

        if not rag_chain:
            logger.error("RAG chain initialization failed")
            return False

        # Test query
        test_query = "Hello, can you summarize the documents?"
        logger.info(f"Test query: {test_query}")

        response = rag_service.query(test_query)

        logger.info("✅ Test completed successfully!")
        logger.info(f"Response: {response['answer'][:200]}...")
        logger.info(f"Source documents used: {len(response.get('context', []))}")

        return True

    except Exception as e:
        logger.error(f"❌ Error in test: {str(e)}")
        return False


if __name__ == "__main__":
    # Show statistics
    stats = DocumentProcessor.get_document_stats(config.data_dir)
    print(f"\n📊 Document Statistics:")
    print(f"Total files: {stats['total_files']}")
    print(f"PDFs found: {stats['pdf_count']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"PDF files: {stats['pdf_files']}\n")

    # Run test
    if stats['pdf_count'] > 0:
        success = test_rag_system()
        sys.exit(0 if success else 1)
    else:
        logger.error("No PDF files found in data directory")
        sys.exit(1)
