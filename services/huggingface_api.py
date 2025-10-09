import os
import time
import logging
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

HF_HEADERS = {"Authorization": f"Bearer {os.getenv('HF_API_KEY', '')}"}
HF_BASE = "https://api-inference.huggingface.co/models"

def hf_post(model, payload, retry=2):
    url = f"{HF_BASE}/{model}"
    for attempt in range(retry + 1):
        resp = requests.post(url, headers=HF_HEADERS, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"HF call {model} status {resp.status_code} attempt {attempt}: {resp.text}")
            time.sleep(1 + attempt)
    raise Exception(f"Hugging Face API failed for {model}: {resp.status_code} {resp.text}")

# -------------------------
# Embeddings
# -------------------------
def get_embeddings(model, text):
    """
    Calls HF feature-extraction to get embeddings for a single text.
    Returns 1D list of floats.
    """
    payload = {"inputs": text}
    out = hf_post(model, payload)

    if isinstance(out, list):
        candidate = out[0]
        if candidate and isinstance(candidate[0], list):
            # Average token embeddings
            import numpy as np
            arr = np.array(candidate)
            vec = arr.mean(axis=0).tolist()
            return vec
        elif candidate and isinstance(candidate[0], (float, int)):
            return candidate
    raise Exception("Unexpected HF embeddings response format")

# -------------------------
# Cross Encoder
# -------------------------
def get_cross_encoder_score(model, student, teacher):
    """
    Try different input formats to obtain a similarity/score between student and teacher.
    Returns float between 0 and 1 (or raises).
    """
    try:
        payload = {"inputs": [student, teacher]}
        out = hf_post(model, payload)
        if isinstance(out, list) and len(out) and isinstance(out[0], dict) and "score" in out[0]:
            return float(out[0]["score"])
        if isinstance(out, list) and len(out) and isinstance(out[0], (float, int)):
            return float(out[0])
    except Exception:
        logger.exception("Format [student, teacher] failed")

    try:
        payload = {"inputs": {"text_pair": [student, teacher]}}
        out = hf_post(model, payload)
        if isinstance(out, dict) and "score" in out:
            return float(out["score"])
    except Exception:
        logger.exception("Format text_pair failed")

    try:
        payload = {"inputs": f"{student}\n\n===\n\n{teacher}"}
        out = hf_post(model, payload)
        if isinstance(out, list) and len(out) and isinstance(out[0], dict) and "score" in out[0]:
            top = max(out, key=lambda x: x.get("score", 0.0))
            return float(top.get("score", 0.0))
    except Exception:
        logger.exception("Concatenation fallback failed")

    raise Exception("Unable to parse cross-encoder output")

# -------------------------
# Feedback Generation
# -------------------------
def generate_feedback(question, answer, score, model="meta-llama/Llama-3.2-1B-Instruct:novita"):
    try:
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_API_KEY", "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"),
        )
        completion = client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": f"""
                        You are an educational assistant. Your task is to help students improve their understanding.
                        Given a question, a student’s answer, and the score, generate constructive, encouraging feedback.

                        Follow this format:
                        Positive: <what the student did well>
                        Improvement: <what is missing or could be improved>
                        Suggestion: <what to study or focus on next>

                        Question: {question}
                        Student Answer: {answer}
                        Score: {score}/100
                        """
                                }
                            ],
                        )

        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("error", e)
        logger.warning(f"Feedback generation failed: {e}")
        return f"Good attempt! You scored {score}/100."