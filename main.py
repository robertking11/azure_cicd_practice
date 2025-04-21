from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import OneHotEncoder
import pandas as pd
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Connection string
def get_db_connection():
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER=rk-fastapi-db-server.database.windows.net;"
        f"DATABASE=rk-fastapi-db;"
        f"UID=rk-fastapi-db-server;"
        f"PWD=Poseidon123!;"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return conn

@app.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
def submit_form(
    request: Request,
    age: int = Form(...),
    food: str = Form(...),
    holiday: str = Form(...),
    film: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Read existing users
    df = pd.read_sql("SELECT age, food, holiday, film FROM users", conn)

    # Add new user data
    new_user = {"age": age, "food": food, "holiday": holiday, "film": film}
    new_df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)

    # One-hot encode categorical features
    encoder = OneHotEncoder()
    features = new_df[['food', 'holiday', 'film']]
    encoded = encoder.fit_transform(features).toarray()

    # Add age as a numeric feature
    combined_features = pd.concat([new_df[['age']], pd.DataFrame(encoded)], axis=1)

    # Compute cosine similarity with the last (newest) user
    sim = cosine_similarity([combined_features.iloc[-1]], combined_features[:-1])
    most_similar_index = sim[0].argmax()
    match = df.iloc[most_similar_index]

    # Insert new user into database
    cursor.execute("INSERT INTO users (age, food, holiday, film) VALUES (?, ?, ?, ?)",
                   age, food, holiday, film)
    conn.commit()
    conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "match": match.to_dict()
    })
