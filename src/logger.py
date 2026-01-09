import logging
import sys
import os
import boto3
import io
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis de ambiente de um arquivo .env (útil em desenvolvimento local)
load_dotenv()

# Buffer global em memória para armazenar logs
log_stream = io.StringIO()


def get_logger(name: str) -> logging.Logger:
    """
    Configura um logger que escreve no buffer em memória (para S3) e no console.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Evita adicionar handlers duplicados
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Handler que escreve no buffer em memória (será enviado para o S3)
        stream_handler_s3 = logging.StreamHandler(log_stream)
        stream_handler_s3.setFormatter(formatter)
        logger.addHandler(stream_handler_s3)

        # Handler que escreve no stdout (CloudWatch Logs na Lambda)
        stream_handler_console = logging.StreamHandler(sys.stdout)
        stream_handler_console.setFormatter(formatter)
        logger.addHandler(stream_handler_console)

    return logger


def upload_logs_to_s3():
    """
    Envia o conteúdo do buffer em memória para o S3.
    """
    bucket_name = os.getenv("LOG_BUCKET_NAME")
    region = os.getenv("AWS_REGION")  # na Lambda isso já vem setado automaticamente

    if not bucket_name:
        print("Warning: LOG_BUCKET_NAME not set. Logs will not be uploaded.")
        return

    try:
        # Usa as credenciais providas pela IAM Role da Lambda (não precisa de access key/secret)
        if region:
            s3 = boto3.client("s3", region_name=region)
        else:
            s3 = boto3.client("s3")

        # Gera uma chave única para esse "run"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        key = f"logs/run_{timestamp}.log"

        # Conteúdo dos logs do buffer
        log_content = log_stream.getvalue()

        # Upload pro S3
        s3.put_object(Body=log_content, Bucket=bucket_name, Key=key)
        print(f"Logs successfully uploaded to s3://{bucket_name}/{key}")

        # Opcional: limpar o buffer depois do upload
        log_stream.truncate(0)
        log_stream.seek(0)

    except Exception as e:
        print(f"Failed to upload logs to S3: {e}")
