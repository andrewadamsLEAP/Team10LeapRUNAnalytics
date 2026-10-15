FROM python:3.11-slim
WORKDIR /app

# Install libpq for psycopg database driver
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure start.sh has execute permissions and Unix line endings
RUN chmod +x start.sh && dos2unix start.sh 2>/dev/null || sed -i 's/\r$//' start.sh

CMD ["/bin/bash", "/app/start.sh"]
