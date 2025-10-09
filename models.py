# models.py
from extensions import mongo
import datetime

def users_col():
    return mongo.db.users

def tests_col():
    return mongo.db.tests

def responses_col():
    return mongo.db.responses

def results_col():
    return mongo.db.results

def create_user(name, email, password_hash):
    users_col().insert_one({
        "name": name,
        "email": email,
        "password": password_hash,
        "created_at": datetime.datetime.utcnow()
    })

def find_user_by_email(email):
    return users_col().find_one({"email": email})

def add_test(test_obj):
    tests_col().insert_one(test_obj)

def get_test_by_id(test_id):
    return tests_col().find_one({"id": test_id}, {"_id": 0})

def store_response(email, test_id, question_id, question_text, student_answer, score):
    responses_col().insert_one({
        "email": email,
        "test_id": test_id,
        "question_id": question_id,
        "question_text": question_text,
        "student_answer": student_answer,
        "score": score,
        "timestamp": datetime.datetime.utcnow()
    })

def store_result(email, test_id, total_score, per_question_scores):
    results_col().insert_one({
        "email": email,
        "test_id": test_id,
        "total_score": total_score,
        "per_question_scores": per_question_scores,
        "timestamp": datetime.datetime.utcnow()
    })

def get_user_results(email):
    return list(results_col().find({"email": email}, {"_id": 0}))
