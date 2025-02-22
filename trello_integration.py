import os
import requests
import mysql.connector
from flask import Flask, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure session handling

# Replace with your Trello app credentials
API_KEY = os.getenv("TRELLO_API_KEY") or "06e9d58a7e9a5a80e1d195c6965c1c47"
CALLBACK_URL = "http://localhost:5000/callback"

# MySQL Configuration
DB_HOST = "localhost"  # Change if MySQL is on another server
DB_USER = "root"
DB_PASSWORD = "123456a@"
DB_NAME = "speakly"

# Initialize database connection
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Step 1: Redirect user to Trello for authentication
@app.route("/trello")
def index():
    auth_url = (
        f"https://trello.com/1/authorize?expiration=never"
        f"&name=MyApp&scope=read,write"
        f"&response_type=token&key={API_KEY}"
        f"&redirect_uri={CALLBACK_URL}"
    )
    return f'<a href="{auth_url}">Login with Trello</a>'

# Step 2: Handle Trello OAuth Callback (Store Access Token)
@app.route("/callback")
def callback():
    access_token = request.args.get("token")
    if not access_token:
        return "Authorization failed", 400

    # Fetch Trello user ID (to store token per user)
    url = f"https://api.trello.com/1/members/me?key={API_KEY}&token={access_token}"
    response = requests.get(url)
    if response.status_code != 200:
        return "Failed to fetch Trello user info", 500

    user_data = response.json()
    trello_id = user_data["id"]

    # Store or update token in MySQL
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (trello_id, access_token) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE access_token = VALUES(access_token)",
        (trello_id, access_token)
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Store Trello ID in session
    session["trello_id"] = trello_id
    return redirect("/trello_boards")

# Step 3: Fetch Trello Boards using Stored Token
@app.route("/boards")
def get_boards():
    trello_id = session.get("trello_id")
    if not trello_id:
        return redirect("/")

    # Retrieve stored token from MySQL
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM users WHERE trello_id = %s", (trello_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return redirect("/")  # User must re-login

    access_token = row[0]

    # Use token to fetch boards
    url = f"https://api.trello.com/1/members/me/boards"
    params = {"key": API_KEY, "token": access_token}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        return "Failed to fetch Trello boards", 500

    boards = response.json()
    return jsonify({"boards": [board["name"] for board in boards]})

# Step 4: Logout (Clear Session)
@app.route("/logout")
def logout():
    session.clear()
    return "Logged out. <a href='/'>Login again</a>"

if __name__ == "__main__":
    app.run(debug=True)
