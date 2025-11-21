from flask import Flask, request, redirect, url_for, render_template_string
import os
import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# --- DATABASE CONNECTION & INITIALIZATION ---
def get_db_connection():
    try:
        # 1. Connect to the MySQL Server (Without specifying a DB yet)
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASS')
        )
        
        if conn.is_connected():
            cursor = conn.cursor()
            # 2. Create the specific ISMT database if it doesn't exist
            # This fixes the "Access Denied" error on the 'mysql' system DB
            target_db = os.environ.get('DB_NAME', 'ismt_cloud')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_db}")
            
            # 3. Switch to that database
            conn.database = target_db
            cursor.close()
            return conn
            
    except Error as e:
        print(f"Database Error: {e}")
        return None

# --- SHARED HTML LAYOUT ---
layout = """
<!DOCTYPE html>
<html>
<head>
    <title>ISMT Cloud Portal</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }
        .navbar { background-color: #0078d4; overflow: hidden; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .navbar a { float: left; display: block; color: white; text-align: center; padding: 14px 16px; text-decoration: none; font-size: 18px; font-weight: bold; }
        .navbar a:hover { background-color: #005a9e; border-radius: 4px; }
        .navbar .brand { float: right; color: #b3d9ff; padding: 14px 16px; font-size: 18px; }
        .container { background-color: #ffffff; width: 80%; max-width: 800px; margin: 40px auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #0078d4; }
        input[type=text] { padding: 12px; margin: 8px 0; width: 60%; border: 1px solid #ccc; border-radius: 4px; }
        button { background-color: #28a745; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #218838; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background-color: #f8f9fa; color: #333; }
        .status-box { padding: 15px; margin-top: 20px; border-radius: 5px; text-align: left; background: #e8f4f8; border: 1px solid #d1e4ea; }
        .success { color: green; font-weight: bold; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">📡 Connection Check</a>
        <a href="/guestbook">📝 Student Guestbook</a>
        <div class="brand">ISMT Cloud Portal</div>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- ROUTE 1: HOME ---
@app.route('/')
def home():
    instance_id = os.environ.get('WEBSITE_INSTANCE_ID', 'Local-Dev')[:6]
    conn = get_db_connection()
    
    if conn and conn.is_connected():
        server_info = conn.get_server_info()
        # Get the current database name to prove we aren't in 'mysql' anymore
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        db_status = f"SUCCESS: Connected to '{current_db}' on v{server_info}"
        status_class = "success"
    else:
        db_status = "ERROR: Could not connect to Database."
        status_class = "error"

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=45)

    page_content = f"""
        <h1>System Status Dashboard</h1>
        <div class="status-box">
            <p><strong>App Instance:</strong> {instance_id}</p>
            <p><strong>Database Status:</strong> <span class="{status_class}">{db_status}</span></p>
            <p><strong>Server Time:</strong> {now.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

# --- ROUTE 2: GUESTBOOK ---
@app.route('/guestbook', methods=['GET', 'POST'])
def guestbook():
    conn = get_db_connection()
    message = ""
    
    if not conn:
        return render_template_string(layout.replace('{% block content %}{% endblock %}', "<h3>Database Connection Failed</h3>"))

    cursor = conn.cursor(dictionary=True)

    # 1. Create Table (Auto-Migration)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Error as e:
        return f"Table Creation Failed: {e}"

    # 2. Handle Write
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        if visitor_name:
            cursor.execute("INSERT INTO visitors (name) VALUES (%s)", (visitor_name,))
            conn.commit()
            message = f"<p style='color:green'>Success! {visitor_name} added to Database.</p>"

    # 3. Handle Read
    cursor.execute("SELECT * FROM visitors ORDER BY id DESC LIMIT 10")
    visitors = cursor.fetchall()
    
    cursor.close()
    conn.close()

    rows = ""
    for v in visitors:
        rows += f"<tr><td>{v['id']}</td><td>{v['name']}</td><td>{v['visit_time']}</td></tr>"

    page_content = f"""
        <h1>Student Guestbook</h1>
        {message}
        <form method="POST">
            <input type="text" name="visitor_name" placeholder="Enter Name" required>
            <button type="submit">Sign Guestbook</button>
        </form>
        <br>
        <table>
            <tr><th>ID</th><th>Name</th><th>Time</th></tr>
            {rows}
        </table>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

if __name__ == '__main__':
    app.run()
