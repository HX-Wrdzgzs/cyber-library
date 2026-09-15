FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY web ./web
RUN pip install --no-cache-dir .

VOLUME ["/app/.cyber-library", "/app/data"]
EXPOSE 8080
CMD ["cyber-library", "serve", "--host", "0.0.0.0", "--port", "8080", "--db", "/app/data/catalog.sqlite3"]
