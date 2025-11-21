from flask import Flask
import os
import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

@app.route('/')
def home():
    instance_id = os.environ.get('WEBSITE_INSTANCE_ID', 'Local-Dev')[:6]
    
    # --- REAL DATABASE CONNECTION ---
    db_status = "Connecting..."
    db_host = os.environ.get('DB_HOST')
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASS')
    db_name = os.environ.get('DB_NAME', 'mysql') # Default to system DB if custom one missing

    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            db_status = f"SUCCESS: Connected to MySQL v{db_info}"
            connection.close()
    except Error as e:
        db_status = f"ERROR: {e}"
    # --------------------------------

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=45)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ISMT Cloud Portal</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f4; text-align: center; padding-top: 50px; }}
            .container {{ background-color: #ffffff; width: 600px; margin: 0 auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            h1 {{ color: #0078d4; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: left; background: #f8f9fa; padding: 20px; }}
            .label {{ font-weight: bold; }}
            .value {{ color: #0078d4; font-family: monospace; }}
            .db-box {{ margin-top: 20px; padding: 15px; background: #e8f4f8; border: 1px solid #d1e4ea; border-radius: 5px; text-align: left; }}
            .success {{ color: green; font-weight: bold; }}
            .error {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ISMT College</h1>
            <h3>Real 3-Tier Connectivity Test</h3>
            
            <div class="info-grid">
                <div class="label">App Instance:</div><div class="value">{instance_id}</div>
                <div class="label">Region:</div><div class="value">Southeast Asia</div>
            </div>

            <div class="db-box">
                <strong>Database Connectivity Check:</strong><br>
                <span class="{ 'error' if 'ERROR' in db_status else 'success' }">
                    {db_status}
                </span>
            </div>

            <p>Time (NPT): {now.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run()
