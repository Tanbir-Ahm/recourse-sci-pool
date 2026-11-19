# The Reading Desk as a container. Build from the repository root:
#   docker build -f ocr_tests/web/deploy/Dockerfile -t reading-desk .
# Everything is installed from Ubuntu's own packages (no pip, no Node): Python, Pillow, python-docx, poppler (PDF files), Tesseract (Assamese, Kannada, Hindi, English and orientation data).
# The PDF-report step (Node and Playwright) is left out: the report opens as HTML and can be printed from the browser.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pil python3-docx poppler-utils tesseract-ocr tesseract-ocr-asm tesseract-ocr-kan tesseract-ocr-hin ca-certificates \
 && rm -rf /var/lib/apt/lists/*
# a user with no login and no privileges; its home is the data volume
RUN useradd --system --uid 10001 --create-home --home-dir /data --shell /usr/sbin/nologin rd
COPY ocr_tests /app/ocr_tests
WORKDIR /app
USER rd
ENV HOME=/data RD_DATA_DIR=/data RD_PDF_REPORTS=off RD_COOKIE_SECURE=1 RD_TRUST_PROXY=1
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python3 -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8080'),timeout=4)" || exit 1
CMD ["python3", "ocr_tests/web/server.py", "--host", "0.0.0.0"]
