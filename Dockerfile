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
    && apt-get install -y --no-install-recommends libreoffice-impress fontconfig curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# The deck's text is set in Tajawal. Real PowerPoint can fall back to the
# font embedded inside the .pptx itself, but LibreOffice's PDF conversion
# only picks up a font it can find on the SYSTEM — otherwise it silently
# substitutes a generic font, so exported PDFs looked visibly different
# from the .pptx despite the file itself being correct. Installing the same
# open-source Tajawal (SIL OFL, from Google Fonts) system-wide fixes that.
RUN mkdir -p /usr/share/fonts/truetype/tajawal \
    && curl -fsSL -o /usr/share/fonts/truetype/tajawal/Tajawal-Regular.ttf \
        https://raw.githubusercontent.com/google/fonts/main/ofl/tajawal/Tajawal-Regular.ttf \
    && curl -fsSL -o /usr/share/fonts/truetype/tajawal/Tajawal-Bold.ttf \
        https://raw.githubusercontent.com/google/fonts/main/ofl/tajawal/Tajawal-Bold.ttf \
    && curl -fsSL -o /usr/share/fonts/truetype/tajawal/Tajawal-Medium.ttf \
        https://raw.githubusercontent.com/google/fonts/main/ofl/tajawal/Tajawal-Medium.ttf \
    && fc-cache -f

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist /frontend/dist

ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST_PATH=/frontend/dist
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
