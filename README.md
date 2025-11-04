# OllaPDF: Your Local Document Chat Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OllaPDF is a powerful, locally-hosted document search application. It allows you to chat with your PDF documents using the power of Large Language Models (LLMs) through Ollama, ensuring your data remains private and secure on your own machine.

## The Problem

Have you ever needed to find specific information buried deep within dozens of PDF files? Traditional search is often not smart enough to understand the context of your questions. OllaPDF solves this by using a Retrieval-Augmented Generation (RAG) pipeline to provide intelligent, context-aware answers.

## Features

*   **Intuitive Chat Interface:** Ask questions in natural language.
*   **Local First:** All processing is done locally. Your documents and queries never leave your machine.
*   **Powered by Ollama:** Easily integrate with any model supported by Ollama (e.g., Llama, Mistral, etc.).
*   **Easy to Use:** Simply place your PDFs in a directory and start the application.
*   **Dockerized:** Runs in a container for easy setup and consistent performance.

## Screenshots

Here are some screenshots of the OllaPDF application interface:

<img width="1880" height="977" alt="OllaPDF Application Screenshot 1" src="https://github.com/user-attachments/assets/5132217f-e056-42f5-82f1-66fb3d2e1d4d" />
<img width="1880" height="977" alt="OllaPDF Application Screenshot 2" src="https://github.com/user-attachments/assets/ad20b49f-d340-4adf-b162-e943731f8991" />
<img width="1880" height="977" alt="OllaPDF Application Screenshot 3" src="https://github.com/user-attachments/assets/b7742936-dc65-4235-8dd7-ad4569b9e62c" />
<img width="1880" height="977" alt="OllaPDF Application Screenshot 4" src="https://github.com/user-attachments/assets/c8a055d4-3cb0-4a44-b50d-b18e4640a72d" />


## How It Works



OllaPDF uses a RAG (Retrieval-Augmented Generation) architecture:

1.  **Document Loading:** PDFs in the `data` directory are loaded and split into smaller chunks.
2.  **Vector Embeddings:** The text chunks are converted into numerical representations (embeddings) using a sentence-transformer model.
3.  **Vector Store:** These embeddings are stored in a FAISS vector store for efficient searching.
4.  **Retrieval:** When you ask a question, the application searches the vector store for the most relevant document chunks.
5.  **Generation:** The retrieved chunks are passed as context to an LLM (via Ollama), which then generates a natural language answer.

## Tech Stack

*   **Backend:** Python
*   **Web Framework:** Streamlit
*   **LLM Orchestration:** LangChain
*   **LLM Provider:** Ollama
*   **Vector Store:** FAISS
*   **Containerization:** Docker

## Getting Started

This project is designed to be easy to set up and run using Docker Compose.

### Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Clone the Repository

```bash
git clone https://github.com/manzolo/ollapdf.git
cd ollapdf
```

### 2. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.dist .env
# Open .env in your editor and modify variables as needed
```

This file (`.env`) is used to configure variables like `OLLAMA_HOST` and `OLLAMA_MODEL_NAME`.

### 3. Add Your Documents

Place your PDF files into the `data/` directory. A sample PDF (`sample.pdf`) is included to demonstrate the application's functionality.

### 3. Start the Application

There are three ways to run the application, depending on your needs.

**Option 1: I already have Ollama running**

If you have your own instance of Ollama running, you can start the OllaPDF application by itself:

```bash
docker compose up -d --build
```

The OllaPDF container will be named `manzolo-ollapdf-rag`, which can be useful for commands like `docker exec` or `docker logs`.

**Option 2: I want to run Ollama in a CPU container**

If you want to run both OllaPDF and Ollama as containers, use the `docker-compose.cpu.yml` file:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
```

**Option 3: I want to run Ollama in a GPU container (NVIDIA)**

If you have an NVIDIA GPU, you can run both OllaPDF and Ollama with GPU support using the `docker-compose.gpu.yml` file:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### 4. Pull an Ollama Model

After starting the services (using Option 2 or 3), you need to pull a language model for Ollama to use. You can do this by executing a command inside the running Ollama container.

1.  **Find the Ollama container ID or name:**
    ```bash
    docker ps
    ```
    Look for the container with `ollama/ollama` in the `IMAGE` column.
    If you are using `docker-compose.cpu.yml` or `docker-compose.gpu.yml`, the Ollama container will be named `manzolo-ollapdf-ollama`.

2.  **Pull a model:**
    The default model is `llama2`. You can pull it with the following command:
    ```bash
    docker exec -it manzolo-ollapdf-ollama ollama pull llama2
    ```

    If you want to use a different model, you can change the `OLLAMA_MODEL_NAME` environment variable in the `docker-compose.yml` file and pull the corresponding model.

### 5. Access OllaPDF

Open your web browser and navigate to `http://localhost:8501`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

*   [Streamlit](https://streamlit.io/)
*   [LangChain](https://www.langchain.com/)
*   [Ollama](https://ollama.ai/)
