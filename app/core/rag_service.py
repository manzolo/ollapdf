"""RAG (Retrieval-Augmented Generation) service module."""
import logging
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

logger = logging.getLogger(__name__)


class RAGService:
    """Manages RAG pipeline components."""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        ollama_host: str = "http://ollama:11434",
        model_name: str = "llama2",
        temperature: float = 0.1,
        top_k: int = 4,
        timeout: int = 300
    ):
        """
        Initialize RAG service.

        Args:
            embedding_model: HuggingFace embedding model name
            ollama_host: Ollama service URL
            model_name: Ollama model name
            temperature: LLM temperature
            top_k: Number of documents to retrieve
            timeout: LLM request timeout in seconds
        """
        self.embedding_model = embedding_model
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.temperature = temperature
        self.top_k = top_k
        self.timeout = timeout
        self.vector_store: Optional[FAISS] = None
        self.rag_chain = None

    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """
        Create a FAISS vector store from documents.

        Args:
            documents: List of document chunks

        Returns:
            FAISS vector store

        Raises:
            ValueError: If no documents provided
        """
        if not documents:
            raise ValueError("No documents provided to create the vector store")

        logger.info(f"Creating vector store with {len(documents)} documents")
        logger.info(f"Embedding model: {self.embedding_model}")

        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            self.vector_store = FAISS.from_documents(documents, embeddings)
            logger.info("✅ Vector store created successfully")
            return self.vector_store

        except Exception as e:
            logger.error(f"❌ Error creating the vector store: {str(e)}")
            raise

    def setup_rag_chain(self, retriever=None):
        """
        Configure the RAG chain with the Ollama model.

        Args:
            retriever: Optional retriever, uses internal vector store if not provided

        Returns:
            Configured RAG chain

        Raises:
            ValueError: If retriever not provided and vector store not initialized
        """
        if retriever is None:
            if self.vector_store is None:
                raise ValueError("Vector store not initialized. Call create_vector_store first.")
            retriever = self.vector_store.as_retriever(search_kwargs={"k": self.top_k})
        else:
            # Update retriever's search kwargs
            retriever.search_kwargs.update({"k": self.top_k})

        logger.info(f"Configuring RAG chain:")
        logger.info(f"  - Ollama Host: {self.ollama_host}")
        logger.info(f"  - Model: {self.model_name}")
        logger.info(f"  - Temperature: {self.temperature}")
        logger.info(f"  - Top-K retrieval: {self.top_k}")

        try:
            # Configure the LLM model
            llm = ChatOllama(
                base_url=self.ollama_host,
                model=self.model_name,
                temperature=self.temperature,
                timeout=self.timeout,
                num_predict=-1,  # No limit on response length
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

            # Create RAG chain
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            self.rag_chain = create_retrieval_chain(retriever, question_answer_chain)

            logger.info("✅ RAG chain configured successfully")
            return self.rag_chain

        except Exception as e:
            logger.error(f"❌ Error configuring the RAG chain: {str(e)}")
            raise

    def initialize(self, documents: List[Document]):
        """
        Initialize complete RAG pipeline from documents.

        Args:
            documents: List of document chunks

        Returns:
            Configured RAG chain
        """
        if not documents:
            logger.error("No documents provided")
            return None

        try:
            self.create_vector_store(documents)
            return self.setup_rag_chain()
        except Exception as e:
            logger.error(f"Error initializing RAG service: {str(e)}")
            return None

    def query(self, question: str) -> dict:
        """
        Query the RAG system.

        Args:
            question: User question

        Returns:
            Response dictionary with answer and context

        Raises:
            ValueError: If RAG chain not initialized
        """
        if self.rag_chain is None:
            raise ValueError("RAG chain not initialized. Call setup_rag_chain first.")

        logger.info(f"Processing query: {question}")
        try:
            response = self.rag_chain.invoke({"input": question})
            logger.info("✅ Query processed successfully")
            return response
        except Exception as e:
            logger.error(f"❌ Error processing query: {str(e)}")
            raise
