[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/WyjuINsj)

# Titanic Survival Prediction

ML service that trains a logistic regression on the Titanic dataset and exposes a prediction entrypoint. Includes local training/prediction scripts and IaC for AWS deployment.

The process and train scripts, as well as the train and test data files originate from the following Kaggle page:
[https://www.kaggle.com/code/nadintamer/titanic-survival-predictions-beginner/](https://www.kaggle.com/code/nadintamer/titanic-survival-predictions-beginner/)

**Authors**: Vinícius Rodrigues de Freitas e Raul Rangel Moraes Bezerra

**Video**: [https://youtu.be/TEkEJ3m6kkE](https://youtu.be/TEkEJ3m6kkE)

---

## Tech stack

* **Language**: Python 3.10+
* **ML**: scikit-learn (LogisticRegression)
* **Data versioning**: DVC (local remote in `dvc_storage/`)
* **Deployment**: AWS Lambda + API Gateway + ECR (via Terraform)
* **Container runtime**: Docker (Lambda container image)
* **Logging**:

  * Stdout → CloudWatch Logs (Lambda)
  * In-memory buffer → S3 (application logs)
* **(Optional)** Experiment tracking: MLflow (when enabled in `train.py`)

---

## Repository structure

* [src/](src/) - application code

  * [src/train.py](src/train.py) — training pipeline (reads CSVs, trains model, saves artifact)
  * [src/predict.py](src/predict.py) — Lambda handler & local prediction CLI
  * [src/process.py](src/process.py) — data loading and preprocessing utilities
  * [src/logger.py](src/logger.py) — logging utilities (console + S3)
  * [src/read_logs.py](src/read_logs.py) — helper to read uploaded logs from S3
  * [src/Dockerfile](src/Dockerfile) — container entry for AWS Lambda
  * [src/models/](src/models/) — saved model artifacts (`titanic_model.pkl`)
* [infra/](infra/) - Terraform configuration for deploying Lambda + API Gateway + ECR

  * [infra/main.tf](infra/main.tf)
  * [infra/variables.tf](infra/variables.tf)
  * [infra/outputs.tf](infra/outputs.tf)
  * [infra/versions.tf](infra/versions.tf)
* [data/](data) - small CSVs used by the project (train/test, managed via DVC)
* [dvc_storage/](dvc_storage) - local DVC remote (committed to Git for portability)
* [requirements.txt](requirements.txt) — root dependencies (DVC, etc.)
* [src/requirements.txt](src/requirements.txt) — runtime dependencies for the Lambda image

---

## Configuration

### Environment variables (local & Lambda)

Some behavior depends on environment variables:

* `AWS_REGION`

  * Region used by boto3 clients (e.g. S3).
  * In Lambda this is automatically set by AWS.

* `LOG_BUCKET_NAME`

  * S3 bucket used by `logger.upload_logs_to_s3()` to store application logs.
  * Must exist and be accessible by the IAM role/user running the code.

* (Optional) `AWS_PROFILE` (local only)

  * If using named profiles with `aws-cli`, you can set this before running scripts locally.

Additional environment variables may be introduced in the infra (for example, to configure the API stage name, model version, etc.) – see [`infra/variables.tf`](infra/variables.tf).

---

## Data & preprocessing

* Raw data is expected in [data/](data) and is pulled via DVC.

  * `data/train.csv`
  * `data/test.csv`
* All preprocessing used for both training and inference is implemented in [`process.preprocess`](src/process.py). This ensures **consistency** between `train.py` and `predict.py`.

Key preprocessing steps:

* Missing values:

  * `Age` → median
  * `Fare` → median
  * `Embarked` → `"S"`
* Categorical encoding:

  * `Sex`: `{'male': 0, 'female': 1}`
  * `Embarked`: `{'S': 0, 'C': 1, 'Q': 2}`
* Dropped columns: `Name`, `Ticket`, `Cabin`, `PassengerId`
* Target:

  * Column `Survived`
* Features:

  * All remaining columns after preprocessing (e.g., `Pclass`, `Sex`, `Age`, `SibSp`, `Parch`, `Fare`, `Embarked`).

---

## Quickstart — Local

### 1. Create a Python venv and install deps

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r src/requirements.txt     # ensure runtime deps are installed as well
```

### 2. Pull data (DVC)

This project uses DVC with a git-tracked local remote for easy reproduction.

```bash
dvc pull
```

This will populate the [data/](data) folder with `train.csv` and `test.csv`.

### 3. Train locally

```bash
python src/train.py
```

* Reads `data/train.csv`
* Preprocesses data
* Trains a `LogisticRegression` model
* Saves model to: `src/models/titanic_model.pkl`
* Logs are printed to console; if `LOG_BUCKET_NAME` is set, they are also uploaded to S3 on completion.

### 4. Predict locally

```bash
python src/predict.py
```

This runs a simple example prediction (hard-coded passenger in `__main__`) and prints:

```text
Predição para o passageiro de teste: {'prediction': '0'}
```

You can also import `Passenger` and `predict` in your own scripts:

```python
from predict import Passenger, predict

passenger = Passenger(
    Pclass=3,
    Sex="male",
    Age=22,
    SibSp=1,
    Parch=0,
    Fare=7.25,
    Embarked="S",
)

result = predict(passenger)
print(result)  # {'prediction': '0' or '1'}
```

---

## API contract (Lambda / API Gateway)

The Lambda handler is `predict.handler`.

### Request body (JSON)

The API expects a JSON matching the `Passenger` schema:

```json
{
  "Pclass": 3,
  "Sex": "male",
  "Age": 22,
  "SibSp": 1,
  "Parch": 0,
  "Fare": 7.25,
  "Embarked": "S"
}
```

Where:

* `Pclass` (int): passenger class (1, 2, 3)
* `Sex` (str): `"male"` or `"female"`
* `Age` (float): age in years
* `SibSp` (int): number of siblings/spouses aboard
* `Parch` (int): number of parents/children aboard
* `Fare` (float): fare paid
* `Embarked` (str): `"S"`, `"C"` or `"Q"`

Validation is done via Pydantic (`Passenger` model in `predict.py`). Invalid payloads will raise a validation error and result in a 4xx/5xx from API Gateway/Lambda.

### Response body (JSON)

```json
{
  "prediction": "0"
}
```

Where:

* `prediction` is a string `"0"` or `"1"`:

  * `"1"` → predicted **survived**
  * `"0"` → predicted **did not survive**

---

## Logging

Logging is centralized in [`src/logger.py`](src/logger.py).

* `get_logger(name)`:

  * Configures a `logging.Logger` instance that:

    * Writes to:

      * **in-memory buffer** (`log_stream`) — used later to upload logs to S3
      * **stdout** (`sys.stdout`) — captured by CloudWatch Logs when running in Lambda
* `upload_logs_to_s3()`:

  * Reads everything in the in-memory buffer.
  * Uploads a single `.log` file to the S3 bucket configured via `LOG_BUCKET_NAME`.
  * The key pattern is: `logs/run_YYYY-MM-DD_HH-MM-SS.log`.
  * Clears the buffer afterwards.

Where it is called:

* `train.py`:

  * In the `finally:` block of `train()`, ensuring logs are uploaded even if training fails.
* `predict.py`:

  * At the end of the script when run as `__main__`.
  * In the Lambda handler `handler(...)` after serving a request.

### Reading logs from S3

The helper script [`src/read_logs.py`](src/read_logs.py) can be used to fetch and inspect logs stored in S3 (e.g., for debugging or audit).
Usage example (may vary depending on implementation):

```bash
python src/read_logs.py --bucket-name $LOG_BUCKET_NAME
```

---

## Docker & Lambda

The project uses a **container image** Lambda.

### Building the Docker image (local)

From the `src/` directory:

```bash
cd src
docker build -t titanic-survival-lambda .
```

You can test the image locally (e.g., using `docker run`) if needed.

### Pushing the image to ECR

1. After `terraform apply` (see below), Terraform will create an ECR repository and output its URI (e.g. `123456789012.dkr.ecr.us-east-2.amazonaws.com/titanic-survival`).

2. Authenticate Docker to ECR (region must match your infra):

```bash
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-2.amazonaws.com
```

3. Tag and push the image:

```bash
docker tag titanic-survival-lambda:latest 123456789012.dkr.ecr.us-east-2.amazonaws.com/titanic-survival:latest
docker push 123456789012.dkr.ecr.us-east-2.amazonaws.com/titanic-survival:latest
```

Make sure the tag (`:latest` or another) matches what Terraform expects in [`infra/variables.tf`](infra/variables.tf) or in the `image_uri` used for the Lambda.

---

## Infrastructure — Terraform

The [infra/](infra) folder contains Terraform code to provision:

* ECR Repository (for the Docker image)
* AWS Lambda Function (running the container image)
* API Gateway (HTTP endpoint exposing the Lambda)

### 1. Prerequisites

* `terraform` installed
* `aws-cli` installed and configured

  * Ensure you have credentials with permissions to manage:

    * ECR
    * Lambda
    * API Gateway
    * IAM roles/policies
    * S3 (for logs, if used in infra)

### 2. Initialize and apply

```bash
cd infra
terraform init
terraform apply
```

The `terraform apply` command will output crucial information such as:

* ECR repository URL
* Lambda function name/ARN
* API Gateway endpoint (base URL)

Look for the **Outputs** section at the end of the execution. You may need to:

* Build & push the Docker image to ECR (if not already done).
* Re-run `terraform apply` or update variables if image tags change.

See [`infra/main.tf`](infra/main.tf), [`infra/variables.tf`](infra/variables.tf), and [`infra/outputs.tf`](infra/outputs.tf) for details such as:

* Lambda timeout and memory configuration
* IAM role permissions (e.g. access to S3 log bucket)
* CORS configuration for API Gateway

---

## Testing the Lambda

After deployment, you can test the function using `curl` or Postman. Use the URL provided in the Terraform outputs.

Example:

```bash
curl -X POST "https://sh9m7zkwmj.execute-api.us-east-2.amazonaws.com/dev/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"Pclass\":3,\"Sex\":\"male\",\"Age\":22,\"SibSp\":1,\"Parch\":0,\"Fare\":7.25,\"Embarked\":\"S\"}"
```

* Adjust the URL to match your API Gateway endpoint (from Terraform outputs).
* You can modify the JSON body to test different passenger profiles.

---

## (Optional) Experiment tracking with MLflow

> This section applies if you integrate MLflow in `src/train.py` (not strictly required for the project to run).

Typical setup:

1. Install MLflow in your environment:

   ```bash
   pip install mlflow
   ```

2. Configure environment variables:

   ```bash
   export MLFLOW_TRACKING_URI=file:./mlruns
   export MLFLOW_EXPERIMENT_NAME=titanic-logreg
   ```

3. Inside `train.py`, wrap the training code with MLflow:

   ```python
   import mlflow
   import mlflow.sklearn

   mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
   mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "titanic-default"))

   with mlflow.start_run(run_name="logistic_regression_titanic"):
       mlflow.log_param("model_type", "LogisticRegression")
       mlflow.log_metric("train_accuracy", accuracy)
       mlflow.sklearn.log_model(model, artifact_path="sklearn_model")
   ```

4. To inspect experiments locally:

   ```bash
   mlflow ui --backend-store-uri file:./mlruns
   ```

   Then open the URL shown in the terminal (usually [http://127.0.0.1:5000](http://127.0.0.1:5000)).

---

## Useful files

* [src/train.py](src/train.py) — training pipeline and model save
* [src/predict.py](src/predict.py) — prediction API & CLI example
* [src/process.py](src/process.py) — preprocessing utilities
* [src/logger.py](src/logger.py) — logging and S3 upload
* [src/read_logs.py](src/read_logs.py) — read logs from S3
* [src/Dockerfile](src/Dockerfile) — container definition
* [infra/main.tf](infra/main.tf), [infra/variables.tf](infra/variables.tf), [infra/outputs.tf](infra/outputs.tf) — Terraform IaC

---

## Troubleshooting

* **Data files not found**

  * Error: `"Files not found"` when training or predicting.
  * Fix: run `dvc pull` to fetch `data/train.csv` and `data/test.csv`.

* **Model not found**

  * Error: `"Model not found. Run train.py first."` from `predict.py`.
  * Fix: run `python src/train.py` to create `src/models/titanic_model.pkl`.

* **S3 log upload failing**

  * Check if `LOG_BUCKET_NAME` is set and the bucket exists.
  * Ensure the IAM role/credentials have `s3:PutObject` permission on that bucket.
  * Inspect CloudWatch Logs for full stack traces.

* **Lambda fails due to missing dependencies**

  * Ensure `src/requirements.txt` contains all runtime dependencies.
  * Rebuild the Docker image and push to ECR.
  * Re-deploy (or update the Lambda to use the new image tag).

* **API Gateway returns 4xx/5xx**

  * Verify the JSON body matches the `Passenger` schema.
  * Check CloudWatch Logs for the Lambda function.
  * Confirm that the Lambda was created with the correct image and that `src/models/titanic_model.pkl` is present in the image (train locally and rebuild if necessary).