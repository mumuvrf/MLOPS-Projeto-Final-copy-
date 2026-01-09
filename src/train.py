import os
import joblib
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

import mlflow
import mlflow.sklearn  # para log_model

import process
from logger import get_logger, upload_logs_to_s3

# --- CONFIG ---
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

logger = get_logger(__name__)

# Configuração MLflow
def setup_mlflow():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"file:{BASE_DIR / 'mlruns'}")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "titanic-default")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    logger.info(f"MLflow tracking_uri={tracking_uri}, experiment={experiment_name}")


def train():
    setup_mlflow()

    # Hiperparâmetros
    max_iter = 1000
    random_state = 42

    try:
        logger.info("Starting training pipeline...")

        logger.info("Loading data...")
        df_train, _ = process.load_data()
        n_rows, n_cols = df_train.shape

        logger.info("Preprocessing data...")
        df_processed = process.preprocess(df_train)
        X_train, y_train = process.get_features_and_target(df_processed)

        # Inicia um run no MLflow
        with mlflow.start_run(run_name="logistic_regression_titanic"):
            # ----- Log de parâmetros -----
            mlflow.log_param("model_type", "LogisticRegression")
            mlflow.log_param("max_iter", max_iter)
            mlflow.log_param("random_state", random_state)
            mlflow.log_param("train_rows", n_rows)
            mlflow.log_param("train_cols", n_cols)

            # Treino do modelo
            logger.info("Training Logistic Regression model...")
            model = LogisticRegression(max_iter=max_iter, random_state=random_state)
            model.fit(X_train, y_train)

            # Avaliação
            train_preds = model.predict(X_train)
            accuracy = accuracy_score(y_train, train_preds)
            logger.info(f"Training Accuracy: {accuracy:.4f}")

            # ----- Log de métricas -----
            mlflow.log_metric("train_accuracy", float(accuracy))

            # ----- Persistência local -----
            model_path = MODELS_DIR / "titanic_model.pkl"
            joblib.dump(model, model_path)
            logger.info(f"Model saved to {model_path}")

            # ----- Log de artefatos e do modelo no MLflow -----
            # loga o arquivo salvo
            mlflow.log_artifact(str(model_path), artifact_path="models")
            # e/ou registra o modelo em formato MLflow
            mlflow.sklearn.log_model(model, artifact_path="sklearn_model")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise e

    finally:
        # Envia logs para S3
        upload_logs_to_s3()


if __name__ == "__main__":
    train()
