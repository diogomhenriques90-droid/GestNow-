FROM python:3.11-slim

# Instalar dependências de sistema para PyMuPDF (fitz) e ReportLab
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar as bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código (os teus 16 módulos)
COPY . .

# Porta padrão do Cloud Run
EXPOSE 8080

# Comando para iniciar o Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
