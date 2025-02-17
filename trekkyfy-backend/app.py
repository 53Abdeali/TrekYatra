import eventlet

eventlet.monkey_patch()

from flask import Flask, jsonify, request  # type: ignore
from flask_cors import CORS
from extensions import db, jwt, bcrypt, mail  # type: ignore
from datetime import datetime, timedelta
import os
from routes import register_blueprints
import cloudinary  # type: ignore
import cloudinary.api  # type: ignore
import cloudinary.uploader  # type: ignore
from flask_socketio import SocketIO, emit, join_room
from models import db, User, ChatRequests


# Cloudinary Configuration
cloudinary.config(
    cloud_name="dy7g05pop",
    api_key="354388933296936",
    api_secret="IHZnuyiZxbh7l_eR_5Opo6BbDMY",
)

# App configuration
app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*": {"origins": ["https://trekkyfy.vercel.app", "http://localhost:3000"]}
    },
    supports_credentials=True,
)

secret_key = os.getenv(
    "SECRET_KEY", "66da30be6ce1360c4614b51ed81f8b313847a1920d814d6ef2c07bf2abb28e06"
)
jwt_secret_key = os.getenv(
    "JWT_SECRET_KEY", "bde21c69993e8a62ff9e9cd1d19d8b7bbefda66cc24c2ff29f4bdb25d92592bf"
)

app.config["SECRET_KEY"] = secret_key
app.config["JWT_SECRET_KEY"] = jwt_secret_key
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=10)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://avnadmin:AVNS_P-7RDq_tkUVMeTbEKnV@mysql-21f3bc70-aliabdealifakhri53-78d7.i.aivencloud.com:14791/trekkyfy"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# for forgot password
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "aliabdealifakhri53@gmail.com"
app.config["MAIL_PASSWORD"] = "qenu jgor alhv zoui"

# Enabling web socket using SocketIO
socketio = SocketIO(
    app,
    async_mode="eventlet",
    cors_allowed_origins=["https://trekkyfy.vercel.app", "http://localhost:3000"],
)

online_users = {}
chat_requests = {}

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)
mail.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

register_blueprints(app)


@socketio.on("connect")
def handle_connect():
    user_id = request.args.get("user_id")
    user_type = request.args.get("user_type")  # "guide" or "hiker"

    if user_id and user_type:
        online_users[user_id] = "online"
        eventlet.spawn(update_last_seen(user_id, "online"))
        if user_type == "guide":
            join_room(user_id)
            print(f"Guide {user_id} joined room {user_id}")
        emit("update_status", {"user_id": user_id, "status": "online"}, broadcast=True)
        print(f"{user_type.capitalize()} {user_id} connected via websocket.")
    else:
        print("No user_id or user_type provided on connect.")


@socketio.on("disconnect")
def handle_disconnect():
    user_id = request.args.get("user_id")

    if user_id:
        online_users.pop(user_id, None)
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        eventlet.spawn(update_last_seen(user_id, current_time))
        print(f"User {user_id} disconnected; last_seen updated.")
    else:
        print("No user_id provided on disconnect.")


@socketio.on("chat_request")
def handle_chat_request(data):
    hiker_id = data.get("hiker_id")
    guide_id = data.get("guide_id")
    user_type = data.get("user_type")

    if not hiker_id or not guide_id or user_type != "hiker":
        print("🚨 Invalid chat request: Missing guide_id, hiker_id, or wrong user_type")
        emit(
            "chat_request",
            {"status": "error", "error": "Invalid request"},
            room=hiker_id,
        )
        return

    try:
        eventlet.spawn(process_chat_request, hiker_id, guide_id)
    except Exception as e:
        print(f"🚨 Error handling chat_request: {e}")
        emit("chat_request", {"status": "error", "error": str(e)}, room=hiker_id)


def process_chat_request(hiker_id, guide_id):
    try:
        new_request = ChatRequests(
            hiker_id=hiker_id, guide_id=guide_id, status="pending"
        )
        db.session.add(new_request)
        db.session.commit()

        if guide_id in online_users:
            emit(
                "chat_request",
                {"hiker_id": hiker_id, "guide_id": guide_id},
                room=guide_id,
            )
            print(f"📩 Hiker {hiker_id} sent chat request to Guide {guide_id}")
        else:
            print(f"❌ Guide {guide_id} is not online, request pending.")

        emit("chat_request_response", {"status": "success"}, room=hiker_id)

    except Exception as e:
        db.session.rollback()
        print(f"🚨 Error processing chat request: {e}")
        emit("chat_request", {"status": "error", "error": str(e)}, room=hiker_id)


@socketio.on("chat_response")
def handle_chat_response(data):
    guide_id = data.get("guide_id")
    hiker_id = data.get("hiker_id")
    accepted = data.get("accepted")

    if not guide_id or not hiker_id:
        print("🚨 Missing guide_id or hiker_id in chat_response")
        return

    eventlet.spawn(process_chat_response, guide_id, hiker_id, accepted)


def process_chat_response(guide_id, hiker_id, accepted):
    try:
        request = ChatRequests.query.filter_by(
            hiker_id=hiker_id, guide_id=guide_id, status="pending"
        ).first()

        if request:
            request.status = "accepted" if accepted else "rejected"
            db.session.commit()  # Commit the status change asynchronously

            # Notify the hiker
            emit(
                "chat_response",
                {"guide_id": guide_id, "accepted": accepted},
                room=hiker_id,
            )

            if accepted:
                guide = User.query.filter_by(guide_id=guide_id).first()
                if guide and guide.guide_whatsapp:
                    whatsapp_url = f"https://wa.me/{guide.guide_whatsapp}"
                    emit("whatsapp_link", {"whatsapp_url": whatsapp_url}, room=hiker_id)
                    print(
                        f"✅ Guide {guide_id} accepted chat request, WhatsApp link sent to Hiker {hiker_id}"
                    )
                else:
                    print(
                        f"⚠️ Guide {guide_id} accepted chat request but has no WhatsApp number."
                    )
            else:
                print(
                    f"❌ Guide {guide_id} rejected chat request from Hiker {hiker_id}"
                )
        else:
            print("❌ Chat request not found or already processed.")
    except Exception as e:
        print(f"🚨 Error in handling chat response: {e}")


@socketio.on("heartbeat")
def handle_heartbeat(data):
    user_id = data.get("user_id")

    if user_id:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        update_last_seen(user_id, current_time)
        print(f"Heartbeat received for {user_id}, updated last_seen to {current_time}")
    else:
        print("Heartbeat received with no user_id.")


def update_last_seen(user_id, status):
    eventlet.spawn(process_update_last_seen, user_id, status)


def process_update_last_seen(user_id, status):
    try:
        user = User.query.filter(
            (User.guide_id == user_id) | (User.hiker_id == user_id)
        ).first()

        if user:
            user.last_seen = status
            try:
                db.session.commit()
                print(f"Updated last_seen for user {user_id}: {user.last_seen}")
            except Exception as e:
                db.session.rollback()
                print(f"Error updating last_seen for user {user_id}: {e}")
        else:
            print(f"User {user_id} not found.")
    except Exception as e:
        print(f"Error in updating last_seen: {e}")


# API Health Check
@app.route("/")
def home():
    return jsonify({"message": "The Python app is running successfully on port 5000!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
