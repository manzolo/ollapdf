"""
OllaPDF - Intelligent Document Search Application
Main Streamlit interface
"""
import os
import time
import logging
import requests
import streamlit as st

# Local imports
from config import config
from core import DocumentProcessor, RAGService
from services import RequestQueue
from ui import clean_response, extract_think_content, load_css, render_math_script, get_html_head

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =================================================================
# === Configuration ===
# =================================================================

st.set_page_config(
    page_title="Intelligent Document Search",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =================================================================
# === Initialize Session State ===
# =================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    if "temperature" not in st.session_state:
        st.session_state.temperature = config.default_temperature
    if "chunk_size" not in st.session_state:
        st.session_state.chunk_size = config.default_chunk_size
    if "chunk_overlap" not in st.session_state:
        st.session_state.chunk_overlap = config.default_chunk_overlap
    if "top_k" not in st.session_state:
        st.session_state.top_k = config.default_top_k
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_requests" not in st.session_state:
        st.session_state.pending_requests = {}
    if "request_queue" not in st.session_state:
        st.session_state.request_queue = RequestQueue(
            max_concurrent=config.max_concurrent_requests
        )

init_session_state()

# logger.info("Streamlit session state initialized.")

# =================================================================

# === Styling ===

# =================================================================



# Load CSS and JavaScript

css_content = load_css()

html_head = get_html_head()

math_script = render_math_script()



st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

st.markdown(f"""{html_head}

{math_script}

""", unsafe_allow_html=True)

# logger.info("UI styling and scripts loaded.")

# =================================================================

# === Helper Functions ===

# =================================================================

@st.cache_data(ttl=3600)
def get_ollama_models(host: str):
    """Fetch available models from Ollama server."""
    try:
        if host.startswith("http"):
            resp = requests.get(f"{host}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m['name'] for m in resp.json().get('models', [])]
            logger.info(f"Successfully fetched {len(models)} Ollama models from {host}.")
            return models
        else:
            logger.info(f"Ollama host {host} does not start with http, returning empty model list.")
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to Ollama at {host}. Please check the server status.")
        logger.error(f"Connection error when fetching Ollama models from {host}.")
        return []
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return []


@st.cache_resource(show_spinner=False)
def get_documents(data_dir: str, chunk_size: int, chunk_overlap: int):
    """Load and process documents."""
    processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = processor.load_documents(data_dir)
    if docs:
        logger.info(f"Successfully loaded {len(docs)} documents from {data_dir}.")
    else:
        logger.info(f"No documents found in {data_dir}.")
    return docs


@st.cache_resource(show_spinner=False)
def initialize_rag(model_name: str, temperature: float, top_k: int):
    """Initialize RAG chain."""
    if not model_name:
        logger.warning("RAG chain not initialized: No model name provided.")
        return None

    with st.spinner(f"Loading and analyzing documents with the `{model_name}` model..."):
        try:
            rag_service = RAGService(
                embedding_model=config.embedding_model,
                ollama_host=config.ollama_host,
                model_name=model_name,
                temperature=temperature,
                top_k=top_k,
                timeout=config.llm_timeout
            )
            rag_chain = rag_service.initialize(st.session_state.documents)
            logger.info(f"RAG chain initialized successfully with model: {model_name}, temperature: {temperature}, top_k: {top_k}.")
            return rag_chain
        except Exception as e:
            st.error(f"Failed to initialize RAG chain: {e}")
            logger.error(f"RAG initialization error: {e}")
            return None

# =================================================================
# === Load Documents ===
# =================================================================

try:
    st.session_state.documents = get_documents(
        config.data_dir,
        st.session_state.chunk_size,
        st.session_state.chunk_overlap
    )
    if not st.session_state.documents:
        st.warning(f"No documents found in the '{config.data_dir}' directory.")
except Exception as e:
    st.error(f"Error loading documents: {e}")
    logger.error(f"Document loading error: {e}")
    st.session_state.documents = []

# =================================================================
# === Initialize RAG ===
# =================================================================

if "selected_model_name" in st.session_state and st.session_state.selected_model_name:
    st.session_state.rag_chain = initialize_rag(
        st.session_state.selected_model_name,
        st.session_state.temperature,
        st.session_state.top_k
    )
else:
    st.session_state.rag_chain = None

# =================================================================
# === UI Components ===
# =================================================================

st.title("📚 Intelligent Document Search")
st.caption("Ask questions about your PDF documents and get precise answers")

# === Sidebar ===
with st.sidebar:
    st.header("⚙️ Configuration")

    # Model selection
    ollama_models = get_ollama_models(config.ollama_host)
    if ollama_models:
        default_model = config.ollama_model_name
        selected_model = st.selectbox(
            "Select Model",
            options=ollama_models,
            index=ollama_models.index(default_model) if default_model in ollama_models else 0,
            key="selected_model_name"
        )
    else:
        st.warning("No models available.")
        selected_model = None

    st.markdown("---")

    # RAG Configuration
    st.header("⚙️ RAG Configuration")
    st.session_state.temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.temperature,
        step=0.05,
        key="temperature_slider",
        help="Controls the randomness of the model's output. Higher values mean more creative, lower values mean more deterministic."
    )
    st.session_state.chunk_size = st.number_input(
        "Chunk Size",
        min_value=100,
        max_value=2000,
        value=st.session_state.chunk_size,
        step=50,
        key="chunk_size_input",
        help="The maximum number of characters in each document chunk."
    )
    st.session_state.chunk_overlap = st.number_input(
        "Chunk Overlap",
        min_value=0,
        max_value=500,
        value=st.session_state.chunk_overlap,
        step=10,
        key="chunk_overlap_input",
        help="The number of characters to overlap between adjacent chunks. Helps maintain context."
    )
    st.session_state.top_k = st.number_input(
        "Top K Documents",
        min_value=1,
        max_value=10,
        value=st.session_state.top_k,
        step=1,
        key="top_k_input",
        help="The number of most relevant documents to retrieve for answering the question."
    )

    st.markdown("---")

    # System Status
    st.header("📊 System Status")
    queue_stats = st.session_state.request_queue.get_queue_stats()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("In Queue", queue_stats['queue_size'])
        st.metric("Active", queue_stats['active_count'])
    with col2:
        st.metric("Processing", queue_stats['processing_count'])
        st.metric("Max Concurrent", queue_stats['max_concurrent'])

    if st.button("🔄 Refresh Status", key="refresh_stats"):
        st.rerun()

    # System Information
    with st.expander("ℹ️ System Information"):
        if st.session_state.documents:
            unique_files = sorted(list(set(
                doc.metadata.get('source_file')
                for doc in st.session_state.documents
            )))
        else:
            unique_files = []

        st.markdown(f"""
        - **Active Model**: `{selected_model}`
        - **Host**: `{config.ollama_host}`
        - **Documents Loaded**: {len(unique_files)}
        """)

        st.subheader("📥 Document Downloads")
        if unique_files:
            for file in unique_files:
                file_path = os.path.join(config.data_dir, file)
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"Download {file}",
                            data=f,
                            file_name=file,
                            mime="application/pdf",
                            key=f"download_{file}"
                        )
                else:
                    st.warning(f"File not found: {file}")

# === Chat Interface ===

# Display message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            if message.get("is_error"):
                st.markdown(message["content"], unsafe_allow_html=True)
            else:
                full_content = f'<div class="assistant-message">{message["content"]}</div>'
                st.markdown(full_content, unsafe_allow_html=True)

                if "think_content" in message and message["think_content"]:
                    with st.expander("🧠 Show reasoning process", expanded=False):
                        for i, think in enumerate(message["think_content"], 1):
                            st.markdown(
                                f'<div class="think-section"><strong>Reasoning {i}:</strong><br>{think.strip()}</div>',
                                unsafe_allow_html=True
                            )
        elif message["role"] == "user":
            st.markdown(message["content"])

# Handle completed requests
for request_id in list(st.session_state.pending_requests.keys()):
    request_data = st.session_state.request_queue.get_request_status(request_id)

    if request_data and request_data['status'] == 'completed':
        clean_answer, think_content = extract_think_content(request_data['response']["answer"])
        final_answer = clean_response(clean_answer)

        message_data = {"role": "assistant", "content": final_answer}
        if think_content:
            message_data["think_content"] = think_content

        st.session_state.messages.append(message_data)
        del st.session_state.pending_requests[request_id]
        logger.info(f"Request {request_id} completed successfully.")
        st.rerun()

    elif request_data and request_data['status'] == 'error':
        error_msg = f'<div class="error-status"><i class="fas fa-exclamation-triangle"></i> Error: {request_data.get("error", "Unknown error")}</div>'
        st.session_state.messages.append({"role": "assistant", "content": error_msg, "is_error": True})
        del st.session_state.pending_requests[request_id]
        logger.error(f"Request {request_id} failed with error: {request_data.get("error", "Unknown error")}")
        st.rerun()

# Chat input
if prompt := st.chat_input("Type your question here..."):
    logger.info(f"User submitted prompt: {prompt}")
    if st.session_state.rag_chain is None:
        st.warning("Please select an Ollama model before submitting a question.")
    elif not st.session_state.documents:
        st.warning("No documents loaded. Please add files to the 'data' directory.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

        request_id = f"req_{int(time.time() * 1000)}"
        st.session_state.request_queue.add_request(
            request_id,
            prompt,
            st.session_state.rag_chain
        )
        st.session_state.pending_requests[request_id] = True

        st.rerun()

# Polling for pending requests
pending_rids = list(st.session_state.pending_requests.keys())
if pending_rids:
    rid = pending_rids[0]
    data = st.session_state.request_queue.get_request_status(rid)

    with st.chat_message("assistant"):
        ph = st.empty()

        if data and data['status'] == 'processing':
            ph.markdown(
                '<div class="processing-status"><i class="fas fa-cog fa-spin"></i> Processing...</div>',
                unsafe_allow_html=True
            )
        elif data and data['status'] == 'queued':
            p = st.session_state.request_queue.get_queue_position(rid)
            ph.markdown(
                f'<div class="queue-status"><i class="fas fa-clock"></i> Waiting...<br>Position: {p + 1}</div>',
                unsafe_allow_html=True
            )

        # Polling Loop
        if data and data['status'] in ['queued', 'processing']:
            time.sleep(1)
            st.button("...", key="hidden_poll_trigger", disabled=True, type="secondary")
            st.rerun()

with st.expander("ℹ️ Queue System Information", expanded=False):
    st.markdown("Only one request processed at a time (GPU optimization). FIFO order. Auto-refresh.")
