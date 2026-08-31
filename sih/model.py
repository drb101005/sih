import joblib
import numpy as np
import pandas as pd


artifact = joblib.load("risk_model_v3_50.pkl")

model = artifact["model"]
preprocessor = artifact["preprocessor"]
all_features = artifact["all_features"]


def predict_probability_of_failure(data: dict) -> float:

    input_data = {
        feature: data.get(feature)
        for feature in all_features
    }
    X = pd.DataFrame([input_data])

    X_prepared = preprocessor.transform(X)

    prediction = model.predict(X_prepared)[0]

    risk_probability = float(np.clip(prediction, 0.0, 1.0))

    return risk_probability