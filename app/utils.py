import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Import per LangChain v1.0
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# LEGACY CHAINS: ORA IN langchain-classic (NON in langchain-community!)
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_documents(data_dir: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Carica e processa tutti i PDF dalla cartella specificata"""
    if not os.path.exists(data_dir):
        logger.error(f"Directory {data_dir} not found!")
        return []
    
    documents = []
    pdf_files = []
    
    # Trova tutti i file PDF
    for filename in os.listdir(data_dir):
        if filename.lower().endswith(".pdf"):
            pdf_files.append(filename)
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {data_dir}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF files: {pdf_files}")
    
    # Carica ogni PDF
    for filename in pdf_files:
        filepath = os.path.join(data_dir, filename)
        logger.info(f"Loading: {filename}")
        
        try:
            loader = PyPDFLoader(filepath)
            pdf_documents = loader.load()
            
            # Aggiungi info sul file sorgente ai metadati
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
    
    # Splitta i documenti in chunk
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    split_documents = text_splitter.split_documents(documents)
    
    logger.info(f"Documents split into {len(split_documents)} chunks")
    
    # Statistiche per file
    file_stats = {}
    for doc in split_documents:
        source_file = doc.metadata.get('source_file', 'Unknown')
        file_stats[source_file] = file_stats.get(source_file, 0) + 1
    
    logger.info("Chunk statistics per file:")
    for file, count in file_stats.items():
        logger.info(f"  - {file}: {count} chunks")
    
    return split_documents

def create_vector_store(documents: List[Document], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> FAISS:
    """Crea un vector store FAISS dai documenti"""
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
    """
    Configura la RAG chain con il modello Ollama (COMPATIBILE LANGCHAIN v1)
    """
    logger.info(f"Configuring RAG chain:")
    logger.info(f"  - Ollama Host: {ollama_host}")
    logger.info(f"  - Model: {model_name}")
    logger.info(f"  - Temperature: {temperature}")
    logger.info(f"  - Top-K retrieval: {top_k}")
    
    try:
        # Configura il retriever
        retriever.search_kwargs.update({"k": top_k})
        
        # Configura il modello LLM
        llm = ChatOllama(
            base_url=ollama_host,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            num_predict=-1,  # Nessun limite sulla lunghezza della risposta
        )
        
        # Crea il prompt
        system_prompt = (
            "Usa il contesto fornito per rispondere alla domanda. "
            "Se non conosci la risposta, di' che non la sai. "
            "Usa massimo tre frasi e mantieni la risposta concisa. "
            "Context: {context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # ✅ USA LANGCHAIN-CLASSIC per le chains (metodo ufficiale v1)
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        logger.info("✅ RAG chain configured successfully")
        return rag_chain
        
    except Exception as e:
        logger.error(f"❌ Error configuring the RAG chain: {str(e)}")
        raise

# Mantieni le altre funzioni invariate
def get_document_stats(data_dir: str) -> Dict[str, Any]:
    """Ottiene statistiche sui documenti nella cartella"""
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