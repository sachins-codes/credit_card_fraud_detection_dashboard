import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


def load_and_preprocess(filepath):

    # Load Dataset
    df = pd.read_csv(filepath)

    # -----------------------------
    # Remove unwanted columns
    # -----------------------------

    drop_columns = [
        "Transaction_ID",
        "Customer_ID",
        "Card_Number"
    ]

    for col in drop_columns:
        if col in df.columns:
            df.drop(columns=col, inplace=True)

    # -----------------------------
    # Date Features
    # -----------------------------

    if "Transaction_Date" in df.columns:

        df["Transaction_Date"] = pd.to_datetime(
            df["Transaction_Date"]
        )

        df["Year"] = df["Transaction_Date"].dt.year
        df["Month"] = df["Transaction_Date"].dt.month
        df["Day"] = df["Transaction_Date"].dt.day

        df.drop(columns="Transaction_Date", inplace=True)

    # -----------------------------
    # Time Features
    # -----------------------------

    if "Transaction_Time" in df.columns:

        df["Hour"] = (
            pd.to_datetime(
                df["Transaction_Time"]
            ).dt.hour
        )

        df.drop(columns="Transaction_Time", inplace=True)

    # -----------------------------
    # Encode categorical columns
    # -----------------------------

    encoders = {}

    categorical = df.select_dtypes(
        include=["object"]
    ).columns

    for col in categorical:

        encoder = LabelEncoder()

        df[col] = encoder.fit_transform(
            df[col].astype(str)
        )

        encoders[col] = encoder

    # -----------------------------
    # Split Features & Target
    # -----------------------------

    X = df.drop("Class", axis=1)

    y = df["Class"]

    # -----------------------------
    # Train Test Split
    # -----------------------------

    X_train, X_test, y_train, y_test = train_test_split(

        X,
        y,

        test_size=0.20,

        random_state=42,

        stratify=y

    )

    # -----------------------------
    # Scaling
    # -----------------------------

    scaler = StandardScaler()

    X_train = scaler.fit_transform(X_train)

    X_test = scaler.transform(X_test)

    return (

        X_train,

        X_test,

        y_train,

        y_test,

        scaler,

        encoders

    )