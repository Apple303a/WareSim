from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-only-change-me"

    from app.routes import main
    from app.integration import create_simulation_state

    app.extensions["waresim_state"] = create_simulation_state()
    app.register_blueprint(main)

    return app
