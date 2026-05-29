FROM python:3.11-slim
WORKDIR /app
COPY ../src /app/src
COPY run_role.py /app/run_role.py
RUN pip install --no-cache-dir
ENTRYPOINT ["python", "-u", "/app/run_role.py"]
