from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Initialize Flask app
app = Flask(__name__)

# Load and preprocess data
df = pd.read_csv('creditDS.csv')

# Initialize encoders and scaler
label_encoder_gender = LabelEncoder()
label_encoder_employment = LabelEncoder()
scaler = StandardScaler()

# Fit encoders and scaler
df['Gender'] = label_encoder_gender.fit_transform(df['Gender'])
df['Employment Profile'] = label_encoder_employment.fit_transform(df['Employment Profile'])
df['Income'] = scaler.fit_transform(df[['Income']])

# Prepare the model
X = df.drop(columns=['Credit Score'])
y = df['Credit Score']
model = xgb.XGBRegressor(objective='reg:squarederror', eval_metric='rmse')
model.fit(X, y)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/credit-form', methods=['GET', 'POST'])
def credit_form():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = int(request.form['age'])
        gender = request.form['gender']
        income = float(request.form['income'])
        employment_profile = request.form['employment_profile']

        # Preprocess the input
        gender = label_encoder_gender.transform([gender])[0]
        employment_profile = label_encoder_employment.transform([employment_profile])[0]
        income_scaled = scaler.transform([[income]])[0][0]

        # Create input data for prediction
        input_data = pd.DataFrame({
            'Age': [age],
            'Gender': [gender],
            'Income': [income_scaled],
            'Employment Profile': [employment_profile]
        })

        # Predict the credit score
        predicted_credit_score = model.predict(input_data)

        # Pass the predicted score to the template
        return render_template('credit_form.html', predicted_score=predicted_credit_score[0], name=name)

    return render_template('credit_form.html')

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    app.run(debug=True)
