from flask import Flask
import os
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    # Azure App Service environment variables
    instance_id = os.environ.get('WEBSITE_INSTANCE_ID', 'Local-Dev-Env')[:6]
    python_version = os.environ.get('WEBSITE_PYTHON_VERSION', '3.10')
    
    # Current time in Kathmandu
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=45)
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ISMT Cloud Portal</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f4; text-align: center; padding-top: 50px; }}
            .container {{ background-color: #ffffff; width: 600px; margin: 0 auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            h1 {{ color: #0078d4; }}
            .subtitle {{ color: #666; margin-bottom: 30px; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: left; background: #f8f9fa; padding: 20px; border-radius: 8px; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #0078d4; font-family: monospace; }}
            .footer {{ margin-top: 30px; font-size: 0.9em; color: #888; border-top: 1px solid #eee; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ISMT College</h1>
            <div class="subtitle">Automated CI/CD Deployment</div>
            
            <div class="info-grid">
                <div class="label">Cloud Provider:</div>
                <div class="value">Microsoft Azure (PaaS)</div>
                <div class="label">Region:</div>
                <div class="value">Southeast Asia</div>
                <div class="label">Instance ID:</div>
                <div class="value">{instance_id}</div>
                <div class="label">Deploy Source:</div>
                <div class="value">GitHub Actions</div>
            </div>

            <div class="footer">
                <p>System Operational | Time (NPT): {time_str}</p>
                <p><em>Migrated by Cloud Pulse Pvt Ltd.</em></p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run()
