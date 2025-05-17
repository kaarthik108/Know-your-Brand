FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .
COPY main.py .
COPY custom_database_service.py .
COPY adk/ ./adk/

# Install tar and gzip (required by uv installer), then install uv
RUN yum install -y tar gzip && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Install dependencies using uv
RUN uv pip install -r requirements.txt --target ${LAMBDA_TASK_ROOT} --no-cache-dir

CMD ["main.lambda_handler"]