import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Import for LangChain v1.0
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# LEGACY CHAINS: NOW IN langchain-classic (NOT in langchain-community!)
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_documents(data_dir: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Loads and processes all PDFs from the specified folder"""
    if not os.path.exists(data_dir):
        logger.error(f"Directory {data_dir} not found!")
        return []
    
    documents = []
    pdf_files = []
    
    # Find all PDF files
    for filename in os.listdir(data_dir):
        if filename.lower().endswith(".pdf"):
            pdf_files.append(filename)
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {data_dir}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF files: {pdf_files}")
    
    # Load each PDF
    for filename in pdf_files:
        filepath = os.path.join(data_dir, filename)
        logger.info(f"Loading: {filename}")
        
        try:
            loader = PyPDFLoader(filepath)
            pdf_documents = loader.load()
            
            # Add source file info to metadata
            for doc in pdf_documents:
                doc.metadata.update({
                    'source_file': filename,
                    'source_path': filepath
                })
            
            documents.extend(pdf_documents)
            logger.info(f"✅ Loaded {filename}: {len(pdf_documents)} pages")
            
        except Exception as e:
            logger.error(f"❌ Error loading {filename}: {str(e)}")
            continue
    
    if not documents:
        logger.error("No documents loaded successfully!")
        return []
    
    logger.info(f"Total documents loaded: {len(documents)} from {len(pdf_files)} PDFs")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    split_documents = text_splitter.split_documents(documents)
    
    logger.info(f"Documents split into {len(split_documents)} chunks")
    
    # Statistics per file
    file_stats = {}
    for doc in split_documents:
        source_file = doc.metadata.get('source_file', 'Unknown')
        file_stats[source_file] = file_stats.get(source_file, 0) + 1
    
    logger.info("Chunk statistics per file:")
    for file, count in file_stats.items():
        logger.info(f"  - {file}: {count} chunks")
    
    return split_documents

def create_vector_store(documents: List[Document], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> FAISS:
    """Creates a FAISS vector store from documents"""
    if not documents:
        raise ValueError("No documents provided to create the vector store")
    
    logger.info(f"Creating vector store with {len(documents)} documents")
    logger.info(f"Embedding model: {model_name}")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        vector_store = FAISS.from_documents(documents, embeddings)
        
        logger.info("✅ Vector store created successfully")
        return vector_store
        
    except Exception as e:
        logger.error(f"❌ Error creating the vector store: {str(e)}")
        raise

def setup_rag_chain(
    retriever, 
    ollama_host: str = "http://ollama:11434", 
    model_name: str = "deepseek-r1:32b",
    temperature: float = 0.1,
    timeout: int = 300,
    top_k: int = 4
):
    """Configures the RAG chain with the Ollama model (LANGCHAIN v1 COMPATIBLE)"""
    logger.info(f"Configuring RAG chain:")
    logger.info(f"  - Ollama Host: {ollama_host}")
    logger.info(f"  - Model: {model_name}")
    logger.info(f"  - Temperature: {temperature}")
    logger.info(f"  - Top-K retrieval: {top_k}")
    
    try:
        # Configure the retriever
        retriever.search_kwargs.update({"k": top_k})
        
        # Configure the LLM model
        llm = ChatOllama(
            base_url=ollama_host,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            num_predict=-1,  # Nessun limite sulla lunghezza della risposta
        )
        
        # Create the prompt
        system_prompt = (
            "Use the provided context to answer the question. "
            "If you don't know the answer, say you don't know. "
            "Use a maximum of three sentences and keep the answer concise. "
            "Context: {context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # ✅ USE LANGCHAIN-CLASSIC for chains (official v1 method)
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        logger.info("✅ RAG chain configured successfully")
        return rag_chain
        
    except Exception as e:
        logger.error(f"❌ Error configuring the RAG chain: {str(e)}")
        raise

# Keep other functions unchanged
def get_document_stats(data_dir: str) -> Dict[str, Any]:
    """Gets statistics on documents in the folder"""
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

def test_rag_system(data_dir: str, test_query: str = "Hello, can you summarize the documents?"):
    """
    Tests the RAG system with an example query
    
    Args:
        data_dir: Path to the document folder
        test_query: Test query to use
    """
    logger.info("🧪 Starting RAG system test")
    
    try:
        # Load documents
        documents = load_documents(data_dir)
        if not documents:
            logger.error("No documents loaded")
            return
        
        # Create vector store
        vector_store = create_vector_store(documents)
        retriever = vector_store.as_retriever()
        
        # Configure RAG chain
        rag_chain = setup_rag_chain(retriever)
        
        # Test query
        logger.info(f"Test query: {test_query}")
        response = rag_chain.invoke({"query": test_query})
        
        logger.info("✅ Test completed successfully!")
        logger.info(f"Response: {response['answer'][:200]}...")
        logger.info(f"Source documents used: {len(response['source_documents'])}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    # System test
    DATA_DIR = "data"
    
    # Show statistics
    stats = get_document_stats(DATA_DIR)
    print(f"\n📊 Document Statistics:")
    print(f"Total files: {stats['total_files']}")
    print(f"PDFs found: {stats['pdf_count']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"PDF files: {stats['pdf_files']}")
    
    # Test the system
    if stats['pdf_count'] > 0:
        test_rag_system(DATA_DIR)