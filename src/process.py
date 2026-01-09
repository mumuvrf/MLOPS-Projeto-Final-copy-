import pandas as pd
from pathlib import Path

# --- CONFIG ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def load_data():
    """Loads raw data from the data directory."""
    train_path = DATA_DIR / "train.csv"
    test_path = DATA_DIR / "test.csv"
    
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(f"Files not found in {DATA_DIR}.")

    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    return df_train, df_test

def preprocess(df):
    """
    Cleans and processes data. 
    This function is used for BOTH training and inference to ensure consistency.
    """
    df = df.copy()
    
    # Handle Missing Values
    # Use fixed values or medians to keep it stateless/robust
    df['Age'] = df['Age'].fillna(df['Age'].median())
    df['Fare'] = df['Fare'].fillna(df['Fare'].median())
    df['Embarked'] = df['Embarked'].fillna('S')

    # Categorical Mapping
    # Sex: Male=0, Female=1
    df['Sex'] = df['Sex'].map({'male': 0, 'female': 1})
    
    # Embarked: S=0, C=1, Q=
    df['Embarked'] = df['Embarked'].map({'S': 0, 'C': 1, 'Q': 2})

    # Drop Unusable Features
    # We drop Name, Ticket, and Cabin as they require complex NLP/processing
    drop_cols = ['Name', 'Ticket', 'Cabin', 'PassengerId']
    df = df.drop(columns=drop_cols, errors='ignore')

    return df

def get_features_and_target(df):
    """Separates X (features) and y (target)."""
    # Check if target exists
    if 'Survived' in df.columns:
        y = df['Survived']
        X = df.drop(columns=['Survived'])
    else:
        y = None
        X = df
        
    return X, y