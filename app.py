from flask import Flask, render_template
import config
from extensions import mongo, mail

app = Flask(__name__)
app.config.from_object(config)

# Initialize extensions
mongo.init_app(app)
mail.init_app(app)

# Import blueprints after extensions
from routes.auth import auth_bp
from routes.test_routes import test_bp

app.register_blueprint(auth_bp)
app.register_blueprint(test_bp)

from services.feedback_agent import build_feedback_agent

app.feedback_agent = build_feedback_agent()

@app.route("/")
def home():
    tests = list(mongo.db.tests.find({}, {"_id": 0}))
    return render_template("home.html", tests=tests)

if __name__ == "__main__":
    app.run(debug=True)