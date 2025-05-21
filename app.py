from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder, StandardScaler
import shap
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

# PostgreSQL DB config
DB_HOST = 'localhost'
DB_NAME = 'creditdb'
DB_USER = 'postgres'
DB_PASS = 'postgres'
DB_PORT = '5432'

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your_super_secret_key'  # Use a real secret key in production

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

# Insert credit form data into the database
def insert_credit_data(name, email, phone, age, gender, income, employment_profile, predicted_score, percentile):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Convert NumPy types to Python native types
        age = int(age)
        gender = int(gender)
        income = float(income)
        employment_profile = int(employment_profile)
        predicted_score = float(predicted_score)
        percentile = float(percentile)
        
        print(f"Attempting to insert data: {name}, {email}, {phone}, {age}, {gender}, {income}, {employment_profile}, {predicted_score}, {percentile}")
        cur.execute("""
            INSERT INTO credit_form_data 
            (name, email, phone, age, gender, income, employment_profile, predicted_score, percentile)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, email, phone, age, gender, income, employment_profile, predicted_score, percentile))
        conn.commit()
        print("Data successfully inserted into database")
    except Exception as e:
        conn.rollback()
        print(f"Error inserting credit data: {str(e)}")
        print(f"Error type: {type(e)}")
        raise  # Re-raise the exception to see the full traceback
    finally:
        cur.close()
        conn.close()

# Load and preprocess the dataset
df = pd.read_csv('creditDS.csv', sep=';')

label_encoder_gender = LabelEncoder()
label_encoder_employment = LabelEncoder()
scaler = StandardScaler()

df['Gender'] = label_encoder_gender.fit_transform(df['Gender'])
df['Employment Profile'] = label_encoder_employment.fit_transform(df['Employment Profile'])
df['Income'] = scaler.fit_transform(df[['Income']])

X = df.drop(columns=['Credit Score'])
y = df['Credit Score']
model = xgb.XGBRegressor(objective='reg:squarederror', eval_metric='rmse')
model.fit(X, y)
explainer = shap.Explainer(model, X)

# Routes

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            cur = conn.cursor()
            # Check if the email already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cur.fetchone()
            if existing_user:
                return "User already exists! Please log in instead."

            # Insert new user into the database
            cur.execute("""
                INSERT INTO users (name, email, password) 
                VALUES (%s, %s, %s) RETURNING id
            """, (name, email, hashed_password))
            user_id = cur.fetchone()[0]  # Get the generated user ID
            conn.commit()
            cur.close()
            conn.close()

            # Store user ID and name in session
            session['user_id'] = user_id
            session['user_name'] = name
            return redirect(url_for('home'))  # Redirect to the home page
        except Exception as e:
            conn.rollback()
            print(f"Error during registration: {e}")
            return "An error occurred during registration."
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, password FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()

            if user:
                stored_hashed_password = user[2]

                # Verify the password
                if check_password_hash(stored_hashed_password, password):
                    session['user_id'] = user[0]
                    session['user_name'] = user[1]
                    return redirect(url_for('home'))  # Redirect to the home page
                else:
                    return "Invalid credentials!"
            else:
                return "User does not exist! Please register first."
        except Exception as e:
            print(f"Error during login: {e}")
            return "An error occurred during login."
        finally:
            conn.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/credit-form', methods=['GET', 'POST'])
def credit_form():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            age = int(request.form['age'])
            gender = request.form['gender']
            income = float(request.form['income'])
            employment_profile = request.form['employment_profile']

            gender = label_encoder_gender.transform([gender])[0]
            employment_profile = label_encoder_employment.transform([employment_profile])[0]
            income_scaled = scaler.transform([[income]])[0][0]

            input_data = pd.DataFrame({
                'Age': [age],
                'Gender': [gender],
                'Income': [income_scaled],
                'Employment Profile': [employment_profile]
            })

            predicted_credit_score = model.predict(input_data)
            shap_values = explainer(input_data)

            feature_impact = dict(zip(input_data.columns, shap_values.values[0]))
            sorted_impact = dict(sorted(feature_impact.items(), key=lambda item: abs(item[1]), reverse=True))

            capped_score = min(predicted_credit_score[0], 900)
            percentile = (df['Credit Score'] < capped_score).mean() * 100

            # Save to DB
            insert_credit_data(name, email, phone, age, gender, income, employment_profile, float(capped_score), float(percentile))

            # Plot chart
            plt.figure(figsize=(8, 4))
            plt.hist(df['Credit Score'], bins=30, color='skyblue', edgecolor='black')
            plt.axvline(capped_score, color='red', linestyle='--', label=f'Your Score: {int(capped_score)}')
            plt.title("Credit Score Distribution")
            plt.xlabel("Credit Score")
            plt.ylabel("Number of Individuals")
            plt.legend()

            img_bytes = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_bytes, format='png')
            plt.close()
            img_bytes.seek(0)
            base64_image = base64.b64encode(img_bytes.read()).decode('utf-8')
            percentile_chart = f"data:image/png;base64,{base64_image}"

            return render_template(
                'credit_form.html',
                predicted_score=float(capped_score),
                name=name,
                shap_values={k: float(v) for k, v in sorted_impact.items()},
                percentile=round(percentile, 2),
                percentile_chart=percentile_chart,
                submitted=True
            )
        except Exception as e:
            print(f"Error during credit form submission: {e}")
            return "An error occurred during form submission."

    return render_template('credit_form.html', submitted=False)

if __name__ == '__main__':
    app.run(debug=True)