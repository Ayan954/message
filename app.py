from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import eventlet

# Load environment variables
load_dotenv()

# Eventlet patch
eventlet.monkey_patch()

# Load env variables
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

@app.before_first_request
def create_tables():
    db.create_all()

# Online tracking
users = {}
sid_to_username = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register')
def handle_register(data):
    username = data.get('username')
    if not username:
        return

    existing_user = User.query.filter_by(username=username).first()
    if not existing_user:
        db.session.add(User(username=username))
        db.session.commit()

    users[username] = request.sid
    sid_to_username[request.sid] = username
    emit('user_list', list(users.keys()), broadcast=True)

@socketio.on('private_message')
def handle_private_message(data):
    recipient = data['to']
    message = data['message']
    sender = data['from']

    if recipient in users:
        emit('private_message', {'message': message, 'from': sender}, room=users[recipient])
    else:
        emit('private_message', {'message': f"{recipient} not found", 'from': 'System'}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    username = sid_to_username.get(sid)
    if username:
        users.pop(username, None)
        sid_to_username.pop(sid, None)
        emit('user_list', list(users.keys()), broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)