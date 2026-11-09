FROM node:24-bookworm-slim AS web
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ATLAS_DATA_DIR=/var/lib/atlas
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    && useradd --system --uid 10001 --create-home atlas \
    && install -d -o atlas -g atlas /var/lib/atlas
COPY LICENSE NOTICE ./
COPY server/ ./server/
COPY data/ ./data/
COPY --from=web /build/dist ./web/dist
USER atlas
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
  CMD ["/app/.venv/bin/python", "-c", "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8765/api/health', timeout=2).status == 200"]
CMD ["/app/.venv/bin/uvicorn", "atlas.main:create_app", "--factory", "--app-dir", "server", "--host", "0.0.0.0", "--port", "8765", "--no-proxy-headers"]
