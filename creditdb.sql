CREATE TABLE credit_form_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(15),
    age INTEGER,
    gender VARCHAR(10),
    income FLOAT,
    employment_profile VARCHAR(100),
    predicted_score FLOAT,
    percentile FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL
);

DROP table users ;

select * from users ;

SELECT * from credit_form_data;
