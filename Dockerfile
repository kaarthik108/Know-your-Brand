FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

# Install Node.js and npm (which includes npx)
RUN yum update -y && \
    yum install -y nodejs npm && \
    yum clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PATH="/root/.local/bin:$PATH"

CMD ["main.handler"]