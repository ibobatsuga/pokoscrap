FROM docker:27-cli AS dockercli
FROM python:3.13-slim
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server server
COPY data data
COPY dist dist
ENV POKO_WORKERS=0 POKO_DATA=/data PYTHONDONTWRITEBYTECODE=1
EXPOSE 8765
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
