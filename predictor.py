import joblib
from sklearn.preprocessing import StandardScaler

class Predictor:
    def __init__(self, model_path):
        self.model = joblib.load(model_path)

    def predict(self, df):
        scaler = StandardScaler()
        scaler.fit_transform(df)
        df_scaled = scaler.transform(df)
        df['quality'] = self.model.predict(df_scaled)