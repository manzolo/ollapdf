import os
import re
import streamlit as st
from datetime import datetime
from queue import Queue, Empty
from threading import Thread, Lock
import time
import requests
from utils import load_documents, create_vector_store, setup_rag_chain

# === Configuration ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
DATA_DIR = "data"

st.set_page_config(
    page_title="Intelligent Document Search",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =================================================================
# === Css/Styling ===
# =================================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet">

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>

<style>
    :root {
        --bg: #0d1117; 
        --surface: #161b22; 
        --text: #c9d1d9; 
        --text-secondary: #8b949e; 
        --primary: #58a6ff; 
        --accent: #58a6ff;
        --border: #30363d; 
        --success: #3fb950;
        --warning: #e3b341;
        --error: #f85149;
    }

    .stApp, .main {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Source Sans Pro', -apple-system, sans-serif;
    }

    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: var(--text) !important;
    }
    
    .assistant-message {
        background: var(--surface);
        border-left: 4px solid var(--primary);
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        color: var(--text);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .think-section {
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        font-family: monospace;
        font-size: 0.8em;
        color: var(--text-secondary);
        line-height: 1.4;
    }

    .queue-status {
        background: #3d3000 !important;
        color: var(--warning) !important;
        border: 1px solid #b8860b !important;
        border-radius: 10px;
        padding: 12px;
        margin: 12px 0;
        font-weight: 600;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .queue-status i {
        margin-right: 8px;
    }

    .processing-status {
        background: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px;
        padding: 12px;
        margin: 12px 0;
        font-weight: 600;
        text-align: center;
        box-shadow: 0 2px 6px rgba(88, 166, 255, 0.5);
        animation: pulse 1.8s infinite;
    }
    .processing-status i {
        margin-right: 8px;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    .error-status {
        background: #492a2a !important; 
        color: var(--error) !important;
        border: 1px solid #f85149 !important;
        border-radius: 10px;
        padding: 12px;
        margin: 12px 0;
        font-weight: 600;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .error-status i {
        margin-right: 8px;
    }
</style>

<script>
    function renderMath() {
        if (typeof renderMathInElement !== "undefined") {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false},
                    {left: "\\\\(", right: "\\\\)", display: false},
                    {left: "\\\\[", right: "\\\\]", display: true}
                ],
                throwOnError: false,
                trust: true
            });
        }
    }

    document.addEventListener("DOMContentLoaded", renderMath);
    const observer = new MutationObserver(() => setTimeout(renderMath, 100));
    observer.observe(document.body, { childList: true, subtree: true });
    setInterval(renderMath, 800);
</script>
""", unsafe_allow_html=True)

# === Ollama Models ===
@st.cache_data(ttl=3600)
def get_ollama_models(host):
    try:
        if host.startswith("http"):
            resp = requests.get(f"{host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m['name'] for m in resp.json().get('models', [])]
        else:
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to Ollama at {host}. Please check the server status.")
        return []
    except Exception:
        return []

# === Load Documents ===
if 'documents' not in st.session_state:
    try:
        st.session_state.documents = load_documents(DATA_DIR)
        if not st.session_state.documents:
            st.warning(f"No documents found in the '{DATA_DIR}' directory.")
    except Exception as e:
        st.error(f"Error loading documents: {e}")
        st.session_state.documents = []


# === Request Queue ===
class RequestQueue:
    def __init__(self, max_concurrent=1):
        self.queue = Queue()
        self.active_requests = {}
        self.completed_requests = {}
        self.max_concurrent = max_concurrent
        self.current_processing = 0
        self.lock = Lock()
        self.worker_thread = None
        self.start_worker()

    def start_worker(self):
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.worker_thread = Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()

    def add_request(self, request_id, query, rag_chain):
        data = {
            'id': request_id, 'query': query, 'rag_chain': rag_chain,
            'timestamp': datetime.now(), 'status': 'queued'
        }
        with self.lock:
            self.active_requests[request_id] = data
            self.queue.put(data)
        return request_id

    def get_request_status(self, request_id):
        with self.lock:
            return self.completed_requests.get(request_id) or self.active_requests.get(request_id)

    def get_queue_position(self, request_id):
        with self.lock:
            if request_id not in self.active_requests: return -1
            status = self.active_requests[request_id]['status']
            if status == 'processing': return 0
            if status == 'queued':
                queue_items = list(self.queue.queue)
                for i, req in enumerate(queue_items):
                    if req['id'] == request_id:
                        return i + self.current_processing
        return -1

    def _process_queue(self):
        while True:
            try:
                if self.current_processing < self.max_concurrent:
                    req = self.queue.get(timeout=1)
                    Thread(target=self._execute_rag_request, args=(req,), daemon=True).start()
                else:
                    time.sleep(0.1)
            except Empty:
                time.sleep(0.5)

    def _execute_rag_request(self, req):
        with self.lock:
            self.current_processing += 1
            req['status'] = 'processing'
            req['start_time'] = datetime.now()

        try:
            resp = req['rag_chain'].invoke({"input": req['query']})
            
            with self.lock:
                req['status'] = 'completed'
                req['response'] = resp
                req['end_time'] = datetime.now()
                self.completed_requests[req['id']] = req
                self.active_requests.pop(req['id'], None)
        except Exception as e:
            with self.lock:
                req['status'] = 'error'
                req['error'] = str(e)
                self.completed_requests[req['id']] = req
                self.active_requests.pop(req['id'], None)
        finally:
            with self.lock:
                self.current_processing -= 1
            self.queue.task_done()

if "request_queue" not in st.session_state:
    st.session_state.request_queue = RequestQueue(max_concurrent=1)

# === Utility Functions ===

def process_latex(text):
    """Converte i marcatori LaTeX standard (\\[...\\] e \\(...\\)) in KaTeX ( $$...$$ e $...$)."""
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    return text

def extract_think_content(text):
    think_pattern = r'<think>(.*?)</think>'
    think_matches = re.findall(think_pattern, text, re.DOTALL)
    cleaned_text = re.sub(think_pattern, '', text, flags=re.DOTALL)
    return cleaned_text.strip(), think_matches

def clean_response(text):
    """Pulisce la risposta, applica la formattazione LaTeX e formatta il testo rimanente."""
    text = process_latex(text) 
    text = re.sub(r'^\s*[\-\*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^(#+\s+.+)$', r'**\1**', text, flags=re.MULTILINE)
    return text.strip()

def render_math_content(content):
    return content 

# === Rag Initialization ===
@st.cache_resource(show_spinner=False)
def initialize_rag(model_name):
    if not model_name:
        return None
        
    with st.spinner(f"Loading and analyzing documents with the `{model_name}` model..."):
        try:
            vector_store = create_vector_store(st.session_state.documents)
            retriever = vector_store.as_retriever(search_kwargs={"k": 4})
            return setup_rag_chain(retriever, OLLAMA_HOST, model_name)
        except Exception as e:
            st.error(f"Failed to initialize RAG chain: {e}")
            return None

# Initialize RAG dependent on the selected model
if "selected_model_name" in st.session_state and st.session_state.selected_model_name:
    st.session_state.rag_chain = initialize_rag(st.session_state.selected_model_name)
else:
    st.session_state.rag_chain = None

# === Ui And Chat Logic ===

st.title("📚 Intelligent Document Search")
st.caption("Ask questions about your PDF documents and get precise answers")

with st.sidebar:
    st.header("⚙️ Configuration")
    ollama_models = get_ollama_models(OLLAMA_HOST)
    if ollama_models:
        default_model = os.getenv("OLLAMA_MODEL_NAME", ollama_models[0])
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

    st.header("📊 System Status")
    queue = st.session_state.request_queue
    with queue.lock:
        queue_size = queue.queue.qsize()
        active_count = len(queue.active_requests)
        processing_count = queue.current_processing
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("In Queue", queue_size)
        st.metric("Active", active_count)
    with col2:
        st.metric("Processing", processing_count)
        st.metric("Max Concurrent", queue.max_concurrent)
    
    if st.button("🔄 Refresh Status", key="refresh_stats"):
        st.rerun()
    
    with st.expander("ℹ️ System Information"):
        if st.session_state.documents:
            unique_files = sorted(list(set(doc.metadata.get('source_file') for doc in st.session_state.documents)))
        else:
            unique_files = []
        
        st.markdown(f"""
        - **Active Model**: `{selected_model}`
        - **Host**: `{OLLAMA_HOST}`
        - **Documents Loaded**: {len(unique_files)}
        """)
        
        st.subheader("📥 Document Downloads")
        if unique_files:
            for file in unique_files:
                file_path = os.path.join(DATA_DIR, file)
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

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_requests" not in st.session_state:
    st.session_state.pending_requests = {}

# Show message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            
            if message.get("is_error"):
                st.markdown(message["content"], unsafe_allow_html=True)
            else:
                # *** FINAL SOLUTION FOR THE DIV: Concatenate HTML into a single string ***
                # message["content"] contains text formatted in Markdown and KaTeX
                full_content = f'<div class="assistant-message">{message["content"]}</div>'
                st.markdown(full_content, unsafe_allow_html=True)
                
                if "think_content" in message and message["think_content"]:
                    with st.expander("🧠 Show reasoning process", expanded=False):
                        for i, think in enumerate(message["think_content"], 1):
                            st.markdown(f'<div class="think-section"><strong>Reasoning {i}:</strong><br>{think.strip()}</div>', unsafe_allow_html=True)
        elif message["role"] == "user":
            st.markdown(message["content"])

# Handle completed requests and add them to history
for request_id in list(st.session_state.pending_requests.keys()):
    request_data = st.session_state.request_queue.get_request_status(request_id)
    
    if request_data and request_data['status'] == 'completed':
        # -> clean_response handles LaTeX and cleaning
        clean_answer, think_content = extract_think_content(request_data['response']["answer"])
        final_answer = clean_response(clean_answer)
        
        message_data = {"role": "assistant", "content": final_answer}
        if think_content:
            message_data["think_content"] = think_content
        
        st.session_state.messages.append(message_data)
        del st.session_state.pending_requests[request_id]
        st.rerun() 
    elif request_data and request_data['status'] == 'error':
        error_msg = f'<div class="error-status"><i class="fas fa-exclamation-triangle"></i> Error: {request_data.get("error", "Unknown error")}</div>'
        st.session_state.messages.append({"role": "assistant", "content": error_msg, "is_error": True})
        del st.session_state.pending_requests[request_id]
        st.rerun()

# --- Input And Polling Management ---

if prompt := st.chat_input("Type your question here..."):
    if st.session_state.rag_chain is None:
        st.warning("Please select an Ollama model before submitting a question.")
    elif not st.session_state.documents:
         st.warning("No documents loaded. Please add files to the 'data' directory.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        request_id = f"req_{int(time.time() * 1000)}"
        st.session_state.request_queue.add_request(request_id, prompt, st.session_state.rag_chain)
        st.session_state.pending_requests[request_id] = True
        
        st.rerun()

# Polling Block
pending_rids = list(st.session_state.pending_requests.keys())
if pending_rids:
    rid = pending_rids[0]
    data = st.session_state.request_queue.get_request_status(rid)
    
    with st.chat_message("assistant"):
        ph = st.empty()
        
        if data and data['status'] == 'processing':
            ph.markdown('<div class="processing-status"><i class="fas fa-cog fa-spin"></i> Processing...</div>', unsafe_allow_html=True)
        elif data and data['status'] == 'queued':
            p = st.session_state.request_queue.get_queue_position(rid)
            ph.markdown(f'<div class="queue-status"><i class="fas fa-clock"></i> Waiting...<br>Position: {p + 1}</div>', unsafe_allow_html=True)
        
        # Polling Loop
        if data and data['status'] in ['queued', 'processing']:
            time.sleep(1)
            st.button("...", key="hidden_poll_trigger", disabled=True, type="secondary")
            st.rerun()

with st.expander("ℹ️ Queue System Information", expanded=False):
    st.markdown("Only one request processed at a time (GPU optimization). FIFO order. Auto-refresh.")