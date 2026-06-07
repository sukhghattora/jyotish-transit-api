FROM python:3.11-slim

# Build deps for pyswisseph (needs gcc)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends gcc python3-dev wget && \
    rm -rf /var/lib/apt/lists/*

# Download Swiss Ephemeris data files (high-precision planetary data)
RUN mkdir -p /opt/ephemeris && \
    cd /opt/ephemeris && \
    for file in sepl_18.se1 semo_18.se1 seas_18.se1; do \
      wget -q "https://www.astro.com/ftp/swisseph/ephe/$file" -O "$file" || true; \
    done

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ephemeris.py houses.py panchang_calculator.py ./

ENV PORT=8000
EXPOSE 8000

CMD ["python", "main.py"]
