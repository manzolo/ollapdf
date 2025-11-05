"""Document processing module."""
import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document loading and processing."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize document processor.

        Args:
            chunk_size: Maximum number of characters in each chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def load_documents(self, data_dir: str) -> List[Document]:
        """
        Load and process all PDFs from the specified directory.

        Args:
            data_dir: Path to directory containing PDF files

        Returns:
            List of processed document chunks
        """
        if not os.path.exists(data_dir):
            logger.error(f"Directory {data_dir} not found!")
            return []

        documents = []
        pdf_files = self._find_pdf_files(data_dir)

        if not pdf_files:
            logger.warning(f"No PDF files found in {data_dir}")
            return []

        logger.info(f"Found {len(pdf_files)} PDF files: {pdf_files}")

        # Load each PDF
        for filename in pdf_files:
            filepath = os.path.join(data_dir, filename)
            try:
                pdf_documents = self._load_single_pdf(filepath, filename)
                documents.extend(pdf_documents)
                logger.info(f"✅ Loaded {filename}: {len(pdf_documents)} pages")
            except Exception as e:
                logger.error(f"❌ Error loading {filename}: {str(e)}")
                continue

        if not documents:
            logger.error("No documents loaded successfully!")
            return []

        logger.info(f"Total documents loaded: {len(documents)} from {len(pdf_files)} PDFs")
        logger.info(f"  - Chunk Size: {self.chunk_size}")
        logger.info(f"  - Chunk Overlap: {self.chunk_overlap}")

        # Split documents into chunks
        split_documents = self.text_splitter.split_documents(documents)
        logger.info(f"Documents split into {len(split_documents)} chunks")

        self._log_statistics(split_documents)

        return split_documents

    def _find_pdf_files(self, data_dir: str) -> List[str]:
        """Find all PDF files in directory."""
        pdf_files = []
        for filename in os.listdir(data_dir):
            if filename.lower().endswith(".pdf"):
                pdf_files.append(filename)
        return pdf_files

    def _load_single_pdf(self, filepath: str, filename: str) -> List[Document]:
        """Load a single PDF file."""
        logger.info(f"Loading: {filename}")
        loader = PyPDFLoader(filepath)
        pdf_documents = loader.load()

        # Add source file info to metadata
        for doc in pdf_documents:
            doc.metadata.update({
                'source_file': filename,
                'source_path': filepath
            })

        return pdf_documents

    def _log_statistics(self, documents: List[Document]) -> None:
        """Log chunk statistics per file."""
        file_stats = {}
        for doc in documents:
            source_file = doc.metadata.get('source_file', 'Unknown')
            file_stats[source_file] = file_stats.get(source_file, 0) + 1

        logger.info("Chunk statistics per file:")
        for file, count in file_stats.items():
            logger.info(f"  - {file}: {count} chunks")

    @staticmethod
    def get_document_stats(data_dir: str) -> Dict[str, Any]:
        """
        Get statistics on documents in the directory.

        Args:
            data_dir: Path to directory containing documents

        Returns:
            Dictionary with document statistics
        """
        stats = {
            'total_files': 0,
            'pdf_files': [],
            'total_size_mb': 0,
            'files_info': []
        }

        if not os.path.exists(data_dir):
            return stats

        for filename in os.listdir(data_dir):
            filepath = os.path.join(data_dir, filename)

            if os.path.isfile(filepath):
                stats['total_files'] += 1
                file_size = os.path.getsize(filepath)
                stats['total_size_mb'] += file_size / (1024 * 1024)

                file_info = {
                    'name': filename,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'is_pdf': filename.lower().endswith('.pdf')
                }

                stats['files_info'].append(file_info)

                if file_info['is_pdf']:
                    stats['pdf_files'].append(filename)

        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        stats['pdf_count'] = len(stats['pdf_files'])

        return stats
