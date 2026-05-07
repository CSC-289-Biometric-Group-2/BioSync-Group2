import os
from flask import Flask
import webview

app = Flask(__name__, template_folder='templates', static_folder='static')

app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'biosync.db'),
)

os.makedirs(app.instance_path, exist_ok=True)

from db import init_app
init_app(app)

from auth import bp as auth_bp
app.register_blueprint(auth_bp)

from routes import bp as routes_bp
app.register_blueprint(routes_bp)

from caretaker import bp as caretaker_bp
app.register_blueprint(caretaker_bp)

if __name__ == '__main__':
    window = webview.create_window('BioSync', app)
    webview.start()