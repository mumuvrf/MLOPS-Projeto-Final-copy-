# Use the official AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory to Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN microdnf install -y \
      gcc \
      gcc-c++ \
      make \
      cmake \
      libstdc++-devel && \
    microdnf clean all && \
    rm -rf /var/cache/dnf /var/cache/microdnf

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Run the app
CMD ["predict.handler"]