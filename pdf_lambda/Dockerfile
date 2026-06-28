FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /var/task

# Install only Chromium (not Firefox/WebKit)
RUN playwright install chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

CMD ["handler.handler"]
