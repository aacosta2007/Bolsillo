FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/tmp/.cache

# Librerías de sistema de WeasyPrint (PDF del reporte mensual): Pango/HarfBuzz/Fontconfig.
# https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-ubuntu
# fonts-dejavu-core: tipografía de respaldo por si una nota trae símbolos que Figtree no tiene.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh \
    && useradd --system --no-create-home bolsillo
USER bolsillo

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
