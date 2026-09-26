FROM python:3.13-slim AS builder
WORKDIR /app
# Install build dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the whole project
COPY . .

# Runtime stage
FROM python:3.13-slim
WORKDIR /app
# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app /app
# Switch to non-root user
USER appuser
EXPOSE 8080
# Entrypoint runs the GUI server
CMD [" python\, \-m\, \meta_harness.gui.server\]
