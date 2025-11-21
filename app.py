from flask import Flask, request, render_template_string, redirect, url_for
import os
import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# --- DATABASE CONNECTION & MIGRATION ---
def get_db_connection():
    try:
        # Connect to System DB first to ensure we can create our own DB
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASS'),
            database='mysql',
            autocommit=True 
        )
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # 1. Create/Switch DB
            target_db = 'ismt_cloud'
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_db}")
            conn.database = target_db
            
            # 2. Table: Visitors (The Log)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visitors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. Table: Site Stats (The Counter)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS site_stats (
                    id INT PRIMARY KEY,
                    hits INT
                )
            """)
            # Initialize counter if table is empty
            cursor.execute("INSERT IGNORE INTO site_stats VALUES (1, 0)")
            
            cursor.close()
            return conn
            
    except Error as e:
        print(f"DB Error: {e}")
        return None

# --- SHARED HTML LAYOUT ---
layout = """
<!DOCTYPE html>
<html>
<head>
    <title>ISMT Cloud Portal</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; }
        
        /* Navbar */
        .navbar { background-color: #0078d4; overflow: hidden; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .navbar a { float: left; display: block; color: white; text-align: center; padding: 14px 16px; text-decoration: none; font-size: 18px; font-weight: bold; transition: 0.3s; }
        .navbar a:hover { background-color: rgba(255,255,255,0.2); border-radius: 5px; }
        .navbar .brand { float: right; color: white; padding: 14px 16px; font-size: 18px; font-weight: lighter; }
        
        /* Containers */
        .container { background-color: white; width: 85%; max-width: 900px; margin: 40px auto; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
        
        /* Elements */
        h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .stat-number { font-size: 3em; font-weight: bold; margin: 10px 0; }
        
        /* Forms & Tables */
        input[type=text] { padding: 15px; width: 60%; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
        input[type=text]:focus { border-color: #0078d4; }
        button { padding: 15px 30px; background-color: #0078d4; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #005a9e; transform: translateY(-2px); }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background-color: #f8f9fa; color: #444; padding: 15px; text-align: left; }
        td { padding: 15px; border-bottom: 1px solid #eee; }
        tr:hover { background-color: #fafafa; }
        
        /* Leaderboard Badges */
        .rank-1 { color: #D4AF37; font-weight: bold; } /* Gold */
        .rank-2 { color: #C0C0C0; font-weight: bold; } /* Silver */
        .rank-3 { color: #CD7F32; font-weight: bold; } /* Bronze */
    </style>
</head>
<body>
    <div class="navbar">
        <a href="/">📊 Dashboard</a>
        <a href="/guestbook">✍️ Guestbook</a>
        <div class="brand">ISMT Cloud Portal</div>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- ROUTE 1: DASHBOARD (Read Only) ---
@app.route('/')
def home():
    instance_id = os.environ.get('WEBSITE_INSTANCE_ID', 'Local')[:6]
    conn = get_db_connection()
    hits = 0
    
    if conn:
        cursor = conn.cursor()
        # Increment Global Counter
        cursor.execute("UPDATE site_stats SET hits = hits + 1 WHERE id = 1")
        # Fetch Counter
        cursor.execute("SELECT hits FROM site_stats WHERE id = 1")
        hits = cursor.fetchone()[0]
        cursor.close()
        conn.close()

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=45)

    page_content = f"""
        <h1>Cloud Analytics Dashboard</h1>
        
        <div class="stat-card">
            <div>Total Page Views (Anonymous + Signed)</div>
            <div class="stat-number">{hits}</div>
            <div>Server Time: {now.strftime("%H:%M:%S")}</div>
        </div>

        <h3>System Health</h3>
        <ul>
            <li><strong>App Instance:</strong> {instance_id}</li>
            <li><strong>Region:</strong> Southeast Asia</li>
            <li><strong>Database:</strong> <span style="color:green">● Online (ismt_cloud)</span></li>
        </ul>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

# --- ROUTE 2: GUESTBOOK (Read/Write + Leaderboard) ---
@app.route('/guestbook', methods=['GET', 'POST'])
def guestbook():
    conn = get_db_connection()
    if not conn: return "DB Connection Failed"
    
    cursor = conn.cursor(dictionary=True)

    # HANDLE POST (Write) with Post/Redirect/Get Pattern
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        if visitor_name:
            cursor.execute("INSERT INTO visitors (name) VALUES (%s)", (visitor_name,))
            conn.commit()
            cursor.close()
            conn.close()
            # REDIRECT to self (GET request) to clear browser history
            return redirect(url_for('guestbook'))

    # HANDLE GET (Read)
    
    # 1. Fetch Recent Logs
    cursor.execute("SELECT * FROM visitors ORDER BY id DESC LIMIT 5")
    recent = cursor.fetchall()
    
    # 2. Fetch Leaderboard (Top 3 Frequent Visitors)
    cursor.execute("""
        SELECT name, COUNT(*) as visit_count 
        FROM visitors 
        GROUP BY name 
        ORDER BY visit_count DESC 
        LIMIT 3
    """)
    leaders = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Generate HTML for Logs
    recent_html = ""
    for v in recent:
        recent_html += f"<tr><td>{v['id']}</td><td>{v['name']}</td><td>{v['visit_time']}</td></tr>"

    # Generate HTML for Leaderboard
    leader_html = ""
    rank = 1
    for l in leaders:
        badge = f"rank-{rank}" if rank <= 3 else ""
        leader_html += f"<tr><td class='{badge}'>#{rank}</td><td>{l['name']}</td><td><strong>{l['visit_count']}</strong> visits</td></tr>"
        rank += 1

    page_content = f"""
        <h1>Student Guestbook</h1>
        
        <div style="display:flex; gap:20px;">
            <div style="flex:1;">
                <h3>🖊️ Sign In</h3>
                <form method="POST">
                    <input type="text" name="visitor_name" placeholder="Enter Name (e.g., 'Student 001')" required>
                    <br><br>
                    <button type="submit">Submit Entry</button>
                </form>
                
                <h3>🕒 Recent Entries</h3>
                <table>
                    <tr><th>ID</th><th>Name</th><th>Time</th></tr>
                    {recent_html}
                </table>
            </div>
            
            <div style="flex:1; background:#f9f9f9; padding:20px; border-radius:10px;">
                <h3>🏆 Hall of Fame (Top 3)</h3>
                <p>Who has visited the most?</p>
                <table>
                    {leader_html}
                </table>
            </div>
        </div>
    """
    return render_template_string(layout.replace('{% block content %}{% endblock %}', page_content))

if __name__ == '__main__':
    app.run()
