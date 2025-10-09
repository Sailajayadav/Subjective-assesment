from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import models

test_bp = Blueprint("test", __name__, url_prefix="/test")


@test_bp.before_request
def require_login():
    # allow access to login/signup endpoints
    if 'user' not in session and request.endpoint not in ("auth.login", "auth.signup", "home"):
        # allow accessing home page / static etc
        allowed = ["home", "auth.login", "auth.signup", "static"]
        # simple guard: allow home and auth pages without login
        if request.endpoint and not request.endpoint.startswith("auth"):
            return redirect(url_for("auth.login"))


@test_bp.route("/start/<test_id>", methods=["GET"])
def start(test_id):
    # clear any previous answers in session and load first question
    test = models.get_test_by_id(test_id)
    if not test:
        flash("Test not found", "danger")
        return redirect(url_for("home"))
    session[f"answers_{test_id}"] = {}
    session[f"current_q_{test_id}"] = 0
    return redirect(url_for("test.question", test_id=test_id))


@test_bp.route("/question/<test_id>", methods=["GET", "POST"])
def question(test_id):
    test = models.get_test_by_id(test_id)
    if not test:
        flash("Test not found", "danger")
        return redirect(url_for("home"))
    questions = test.get("questions", [])
    current_index = session.get(f"current_q_{test_id}", 0)
    answers = session.get(f"answers_{test_id}", {})

    if request.method == "POST":
        qid = request.form.get("qid")
        answer_text = request.form.get("answer", "").strip()
        # save answer in session
        answers[qid] = answer_text
        session[f"answers_{test_id}"] = answers
        # move next
        current_index += 1
        session[f"current_q_{test_id}"] = current_index

    # If finished
    if current_index >= len(questions):
        # All answers collected; run agent to evaluate and email
        user = session.get("user")
        if not user:
            flash("Please login to submit test", "danger")
            return redirect(url_for("auth.login"))

        # Use LangGraph feedback agent instead of run_feedback_agent
        result = current_app.feedback_agent.invoke({
            "student_name": user["name"],
            "student_email": user["email"],
            "test_id": test_id,
            "answers_map": answers,
        })

        flash(f"Test submitted. Overall Score: {result['overall']}", "success")
        return redirect(url_for("test.dashboard"))

    # render current question
    q = questions[current_index]
    return render_template(
        "test_question.html",
        question=q,
        index=current_index + 1,
        total=len(questions),
        test_id=test_id,
    )


@test_bp.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("auth.login"))
    results = models.get_user_results(user["email"])
    return render_template("dashboard.html", results=results, user=user)
