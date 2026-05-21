import joblib
import shap
import numpy as np

model = joblib.load("models/risk_model.joblib")
explainer = shap.TreeExplainer(model)

print("Expected value type:", type(explainer.expected_value))
print("Expected value:", explainer.expected_value)
print("Expected value shape:", np.array(explainer.expected_value).shape)