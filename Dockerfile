# Single Cloud Run service: builds the Next.js frontend as a static export,
# then serves it (and the API) from one FastAPI/uvicorn process. See
# backend/main.py's StaticFiles mount and frontend/next.config.mjs's
# `output: "export"` for the two halves of this.
#
# Build: gcloud builds submit --config cloudbuild.yaml .   (from repo root)

# --- Stage 1: build the frontend static export ------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Same-origin deploy — relative "/api/..." calls, not an absolute backend
# URL (see frontend/lib/api.ts's `??` fallback, which respects this exact
# empty string rather than treating it as unset).
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# --- Stage 2: backend + the built frontend -----------------------------------
FROM python:3.11-slim
WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Cloud Run injects PORT.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
