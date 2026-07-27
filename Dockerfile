FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
# libreoffice-impress (not the full suite) converts the generated .pptx to a
# pixel-faithful PDF for the "official copy to share" download — --no-install-recommends
# keeps it to just the Impress filter chain instead of Writer/Calc/etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist /frontend/dist

ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST_PATH=/frontend/dist
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
