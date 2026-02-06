from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Import blueprints
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.views import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Import and register other blueprints (medicines, chatbot, reminders, appointments)
    # temporarily commented out until files are created
    from app.medicines import medicines as medicines_blueprint
    app.register_blueprint(medicines_blueprint)

    from app.chatbot import chatbot as chatbot_blueprint
    app.register_blueprint(chatbot_blueprint)

    from app.appointments import appointments as appointments_blueprint
    app.register_blueprint(appointments_blueprint)
    
    with app.app_context():
        db.create_all()
        # Initialize scheduler here to avoid circular imports if possible, or in main
        from app.reminders import start_scheduler
        start_scheduler(app)

    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))