# services/feedback_agent.py

from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
import models
from services.evaluation import evaluate_answer
# NOTE: You MUST update services/email_service.py to accept and use the html_content argument
from services.email_service import send_email 
from services.huggingface_api import generate_feedback


# ----------------------
# Define State (Updated)
# ----------------------
class AgentState(dict):
    student_name: str
    student_email: str
    test_id: str
    answers_map: Dict[str, str]
    per_question_scores: List[Dict[str, Any]]
    overall: float
    email_body: str
    html_email_body: str  # NEW: Field for the HTML content
    test: Dict[str, Any]


# ----------------------
# Agent Nodes
# ----------------------
def fetch_test(state: AgentState) -> AgentState:
    """Fetch test data from DB."""
    test = models.get_test_by_id(state["test_id"])
    if not test:
        raise ValueError("Test not found")
    state["test"] = test
    return state


def evaluate_answers(state: AgentState) -> AgentState:
    """Evaluate answers using evaluator + llama feedback and generate HTML body."""
    test = state["test"]
    student_email = state["student_email"]
    test_id = state["test_id"]
    answers_map = state["answers_map"]

    questions = test.get("questions", [])
    per_question_scores = []
    
    # OLD: email_parts will remain for the plain text version
    email_parts = []
    # NEW: List to collect HTML snippets for each question
    question_html_parts = []
    total = 0.0

    # CHANGE: Use enumerate to get the question number
    for idx, q in enumerate(questions):
        q_num = idx + 1 # Calculate the question number
        qid = q["id"]
        qtext = q["text"]
        ideal = q.get("ideal_answer", "")
        student_ans = answers_map.get(qid, "")

        # Step 1: Rule-based or ML evaluation
        score, breakdown = evaluate_answer(student_ans, ideal)

        # Step 2: Store raw response
        models.store_response(student_email, test_id, qid, qtext, student_ans, score)

        # Step 3: Generate AI feedback via LLaMA (Ensure services/huggingface_api.py is FIXED!)
        feedback_text = generate_feedback(qtext, student_ans, score)
        
        # Prepare feedback for HTML (replace newlines with <br/>)
        html_feedback = feedback_text.replace('\n', '<br/>')

        per_question_scores.append({
            "question_id": qid,
            "question_text": qtext,
            "student_answer": student_ans,
            "score": score,
            "breakdown": breakdown,
            "feedback": feedback_text,
        })

        # Plain Text Part (Updated to include question number)
        email_parts.append(
            f"Q{q_num}: {qtext}\n"
            f"A: {student_ans}\n"
            f"Score: {score}/100\n"
            f"Feedback: {feedback_text}\n\n"
        )
        
        # NEW: Generate the HTML snippet for the current question
        question_html_parts.append(
            f"""
            <div class="question-block">
                <p style="font-size: 1.1em; font-weight: 600;">Q{q_num}: {qtext}</p>
                <p style="margin-left: 10px;"><strong>Your Answer:</strong> {student_ans}</p>
                <p style="margin-left: 10px;"><strong>Score:</strong> <span style="color: #007bff; font-weight: bold;">{score}/100</span></p>
                <p style="margin-top: 10px;"><strong>Feedback:</strong></p>
                <div class="feedback-box">
                    {html_feedback}
                </div>
            </div>
            """
        )
        total += score

    # Compute overall
    overall = round(total / max(1, len(questions)), 2)
    models.store_result(student_email, test_id, overall, per_question_scores)

    # Save results in state
    state["per_question_scores"] = per_question_scores
    state["overall"] = overall
    
    # Variables for templating
    TEST_TITLE = test.get('title', 'Assessment')
    STUDENT_NAME = state['student_name']
    OVERALL_SCORE = str(overall)
    QUESTION_FEEDBACK_HTML = "".join(question_html_parts)
    
    # Construct the Plain Text Body
    state["email_body"] = (
        f"Dear {STUDENT_NAME},\n\n"
        f"Here is your assessment feedback for test: {TEST_TITLE}\n\n"
        + "".join(email_parts)
        + f"\nOverall Score: {overall}/100\n\nBest regards,\nAssessment Team"
    )

    # NEW: Construct the HTML Body
    state["html_email_body"] = HTML_EMAIL_TEMPLATE.replace(
        "{{ STUDENT_NAME }}", STUDENT_NAME
    ).replace(
        "{{ TEST_TITLE }}", TEST_TITLE
    ).replace(
        "{{ OVERALL_SCORE }}", OVERALL_SCORE
    ).replace(
        "{{ QUESTION_FEEDBACK_HTML }}", QUESTION_FEEDBACK_HTML
    )
    
    return state


def send_feedback_email(state: AgentState) -> AgentState:
    """Send feedback email with results (passing HTML body)."""
    # CHANGE: Pass the new html_email_body to the send_email function
    send_email(
        state["student_email"],
        f"Assessment Feedback - {state['test'].get('title','')}",
        state["email_body"], # Plain text content
        html_content=state["html_email_body"] # HTML content
    )
    return state


# ----------------------
# Build LangGraph
# ----------------------
def build_feedback_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("fetch_test", fetch_test)
    workflow.add_node("evaluate_answers", evaluate_answers)
    workflow.add_node("send_feedback_email", send_feedback_email)

    workflow.set_entry_point("fetch_test")
    workflow.add_edge("fetch_test", "evaluate_answers")
    workflow.add_edge("evaluate_answers", "send_feedback_email")
    workflow.add_edge("send_feedback_email", END)

    return workflow.compile()


# ----------------------
# HTML Email Template (Move this to a services/email_template.py file if possible)
# ----------------------
HTML_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Assessment Feedback</title>
    <style>
        /* CSS for the email template */
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05); overflow: hidden; }
        .header { background-color: #007bff; color: #ffffff; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 20px; color: #333333; }
        .overall-score { text-align: center; margin: 20px 0; padding: 15px; border: 2px solid #28a745; background-color: #e9f7ef; border-radius: 5px; }
        .overall-score h2 { margin: 0 0 5px 0; color: #28a745; }
        .overall-score p { font-size: 2em; font-weight: bold; color: #28a745; margin: 0; }
        .question-block { margin-bottom: 25px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 5px; }
        .question-block strong { color: #007bff; }
        .feedback-box { margin-top: 10px; padding: 12px; background-color: #f8f9fa; border-left: 4px solid #007bff; border-radius: 3px; white-space: pre-wrap; }
        .footer { padding: 20px; text-align: center; font-size: 0.8em; color: #999999; border-top: 1px solid #eeeeee; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Assessment Feedback: {{ TEST_TITLE }}</h1>
        </div>
        <div class="content">
            <p>Dear {{ STUDENT_NAME }},</p>
            <p>Please find your detailed assessment feedback below:</p>

            <div class="overall-score">
                <h2>Overall Score</h2>
                <p>{{ OVERALL_SCORE }}/100</p>
            </div>
            
            {{ QUESTION_FEEDBACK_HTML }}
            
            <p>We encourage you to review the suggested improvements to enhance your understanding of the material.</p>
        </div>
        <div class="footer">
            Best regards,<br>
            The Assessment Team
        </div>
    </div>
</body>
</html>
"""