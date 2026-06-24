FROM python:3.11-slim

WORKDIR /app

# Use Debian mirror (Tsinghua) for faster apt downloads
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (mirror for speed, official PyPI for hash verification)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    -r requirements.txt

# Download spaCy model for Chinese
RUN python -m spacy download zh_core_web_sm

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
