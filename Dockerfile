FROM python:3.12-slim

WORKDIR /app

COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

# Aspetta che Ollama sia pronto
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
