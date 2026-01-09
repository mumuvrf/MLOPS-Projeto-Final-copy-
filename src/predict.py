import json
import joblib
import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict

import process
from logger import get_logger, upload_logs_to_s3

# --- CONFIG ---
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

logger = get_logger(__name__)


class Passenger(BaseModel):
    """
    Representa a entrada do modelo Titanic.
    """
    Pclass: int        # Classe do passageiro (1, 2, 3)
    Sex: str           # "male" ou "female"
    Age: float         # Idade
    SibSp: int         # Nº de irmãos/cônjuges a bordo
    Parch: int         # Nº de pais/filhos a bordo
    Fare: float        # Tarifa paga
    Embarked: str      # Porto de embarque: "S", "C" ou "Q"


def load_model():
    """
    Carrega o modelo treinado salvo por train.py.
    """
    model_path = MODELS_DIR / "titanic_model.pkl"

    if not model_path.exists():
        logger.error("Model not found. Run train.py first.")
        raise FileNotFoundError("Model not found. Run train.py first.")

    logger.info(f"Loading model from {model_path}...")
    model = joblib.load(model_path)
    return model


def predict(
    passenger: Passenger,
    context: Any = None
) -> Dict[str, str]:
    """
    Função de predição que recebe um Passenger (Pydantic) e
    retorna o resultado em forma de dicionário.
    """
    logger.info("Starting prediction for a single passenger...")

    # Carrega o modelo
    model = load_model()

    # Converte o Passenger em dict (compatível com Pydantic v1 e v2)
    try:
        # Pydantic v2
        passenger_dict = passenger.model_dump()
    except AttributeError:
        # Pydantic v1
        passenger_dict = passenger.dict()

    df_input = pd.DataFrame([passenger_dict])

    # Aplica o mesmo pré-processamento usado em train.py
    logger.info("Preprocessing input data...")
    df_processed = process.preprocess(df_input)

    # get_features_and_target retornará X=df, y=None
    X_input, _ = process.get_features_and_target(df_processed)

    logger.info("Generating prediction...")
    pred = model.predict(X_input)[0]

    logger.info(f"Prediction result: {pred}")

    return {
        "prediction": str(pred),
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler para o AWS Lambda.
    Configure o Lambda com o handler: 'predict.handler'
    """
    logger.info(f"Raw event received: {event}")

    # Quando vem via API Gateway, normalmente o payload está em event["body"]
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body
    else:
        # Invocação direta (por exemplo, via console ou SDK)
        data = event

    # Converte o dict em Passenger (validação pelo Pydantic)
    passenger = Passenger(**data)

    # Usa a função de predição principal
    result = predict(passenger, context)

    # Atualiza os logs
    upload_logs_to_s3()

    # Resposta padrão para API Gateway HTTP/REST
    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }


if __name__ == "__main__":
    try:
        # Exemplo de passageiro para teste local
        example_passenger = Passenger(
            Pclass=3,
            Sex="male",
            Age=22,
            SibSp=1,
            Parch=0,
            Fare=7.25,
            Embarked="S",
        )

        result = predict(example_passenger)
        print("Predição para o passageiro de teste:", result)

    except Exception as e:
        logger.error(f"Prediction failed: {e}")

    finally:
        # Upload logs to S3 after prediction
        upload_logs_to_s3()
