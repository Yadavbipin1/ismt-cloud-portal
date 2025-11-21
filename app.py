from flask import Flask, request, render_template_string
import os
import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# --- ROBUST DATABASE CONNECTION LOGIC ---
def get_db_connection():
    debug_log = []
    conn = None
    
    try:
        # STEP 1: Connect to the System DB ('mysql') first
        # We know this works from previous tests
        debug_log.append("Attempting connection to system DB 'mysql'...")
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASS'),
            database='mysql' 
        )
        
        if conn.is_connected():
            debug_log.append("Connected to system DB.")
            cursor = conn.cursor()
            
            # STEP 2: Create the custom database 'ismt_cloud'
            target_db = 'ismt_cloud'
            debug_log.append(f"Creating database '{target_db}' if not exists...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_db}")
            
            # STEP 3: Switch to the new database
            debug_log.append(f"Switching to '{target_db}'...")
            conn.database = target_db
            
            cursor.close()
            return conn, None # Success, No Error
            
    except Error as e:
        # Capture the EXACT error from Azure
        return None, f"SQL Error: {str(e)} | Log: {' > '.join(debug_log)}"

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
        .navbar .brand { float: right; color: #b3d9ff; padding: 14px 16px; font-size: 18px; }
        .container { background-color: #ffffff; width: 80%; max-width: 800px; margin: 40px auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #0078d4; }
        .status-box { padding: 15px; margin-top: 20px; border-radius: 5px; text-align: left; background: #e8f4f8; border: 1px solid #d1e4ea; }
        .success { color: green; font-weight: bold; }
        .error { color: red; font-weight: bold; }
        input[type=text] { padding: 12px; width: 60%; }
        button { padding: 12px 20px; background-color: #28a745; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">📡 Status</a>
        <a href="/guestbook">📝 Guestbook</a>
        <div class="brand">ISMT Cloud</div>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- ROUTE 1: HOME (Debug View) ---
@app.route('/')
def home():
    instance_id = os.environ.get('WEBSITE_INSTANCE_ID', 'Local')[:6]
    conn, error_msg = get_db_connection()
    
    if conn and conn.is_connected():
        # Verify we are in the right DB
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        server_ver = conn.get_server_info()
        cursor.close()
        conn.close()
        
        status_html = f"<span class='success'>SUCCESS: Connected to '{current_db}' (v{server_ver})</span>"
    else:
        # SHOW THE REAL ERROR ON SCREEN
        status_html = f"<span class='error'>FAILURE: {error_msg}</span>"

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=45)

    page_content = f"""
        <h1>System Diagnostics</h1>
        <div class="status-box">
            <p><strong>App Instance:</strong> {instance_id}</p>
            <p><strong>Connectivity Check:</strong><br>{status_html}</p>
            <p><strong>Server Time:</strong> {now.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

# --- ROUTE 2: GUESTBOOK ---
@app.route('/guestbook', methods=['GET', 'POST'])
def guestbook():
    conn, error_msg = get_db_connection()
    message = ""
    
    if not conn:
        return render_template_string(layout.replace('{% block content %}{% endblock %}', f"<h3>DB Error: {error_msg}</h3>"))

    cursor = conn.cursor(dictionary=True)

    try:
        # Create Table in the NEW 'ismt_cloud' database
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        if request.method == 'POST':
            visitor_name = request.form.get('visitor_name')
            if visitor_name:
                cursor.execute("INSERT INTO visitors (name) VALUES (%s)", (visitor_name,))
                conn.commit()
                message = f"<p style='color:green'>Saved: {visitor_name}</p>"

        cursor.execute("SELECT * FROM visitors ORDER BY id DESC LIMIT 5")
        visitors = cursor.fetchall()
        
    except Error as e:
        return f"SQL Operation Failed: {e}"
    finally:
        cursor.close()
        conn.close()

    rows = ""
    for v in visitors:
        rows += f"<tr><td>{v['id']}</td><td>{v['name']}</td><td>{v['visit_time']}</td></tr>"

    page_content = f"""
        <h1>Guestbook</h1>
        {message}
        <form method="POST">
            <input type="text" name="visitor_name" placeholder="Name" required>
            <button type="submit">Sign</button>
        </form>
        <br>
        <table><tr><th>ID</th><th>Name</th><th>Time</th></tr>{rows}</table>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

if __name__ == '__main__':
    app.run()
