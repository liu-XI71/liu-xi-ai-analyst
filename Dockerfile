FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8765 \
    ANALYST_DATA_DIR=/app/var

WORKDIR /app
COPY requirements.txt constraints-tested.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt -c constraints-tested.txt \
    && groupadd --gid 10001 analyst \
    && useradd --uid 10001 --gid analyst --no-create-home analyst

COPY app ./app
COPY web ./web
COPY skills ./skills
COPY evals ./evals
COPY scripts ./scripts
RUN mkdir -p /app/var && chown analyst:analyst /app/var

USER analyst
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8765')+'/api/health',timeout=4)"
CMD ["sh", "scripts/start.sh"]
