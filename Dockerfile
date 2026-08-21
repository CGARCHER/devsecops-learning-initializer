FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Se instala la aplicación y se crea un usuario sin privilegios.
RUN pip install --no-cache-dir . \
    && addgroup -S initializer \
    && adduser -S initializer -G initializer

USER initializer

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=2)"

CMD ["python", "-m", "devsecops_initializer.web", "--host", "0.0.0.0", "--port", "8080"]
