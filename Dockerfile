FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Update pip and set mirror with retries and longer timeout
RUN pip install --upgrade pip --retries 10 --timeout 120
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt
RUN pip install --no-cache-dir gunicorn  # Ensure gunicorn is installed explicitly

# Install postgresql-client and ping for network testing
RUN apt-get update && apt-get install -y postgresql-client iputils-ping && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "user_auth_project.wsgi:application"]