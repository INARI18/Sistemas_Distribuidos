# Single image shared by both roles (database and health post). Which role a
# container plays is decided by the command docker-compose gives it, not by the
# image -- the simulation has no third-party dependencies, so the image is just
# the standard-library Python runtime plus the source tree.
FROM python:3.11-slim

# Unbuffered stdout so logs (and the final report) appear live in `compose up`.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/ ./src/
COPY db_server.py post_runner.py ./

# Default command runs the database; the health-post service overrides it.
CMD ["python", "db_server.py"]
