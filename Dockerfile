FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

# Install Node.js and npm, and other system dependencies
RUN yum update -y && \
    yum install -y curl gcc libpq-devel && \
    curl -fsSL https://rpm.nodesource.com/setup_lts.x | bash - && \
    yum install -y nodejs && \
    yum clean all && \
    rm -rf /var/cache/yum

# Install system dependencies for psycopg2 and other potential build requirements
# RUN yum update -y && \
#     yum install -y gcc libpq-devel && \
#     yum clean all && \
#     rm -rf /var/cache/yum
    
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PATH="/root/.local/bin:$PATH"

CMD ["main.handler"]