import os
import logging
import nltk
import torch
import requests
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# NLP preprocessing
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))
negation_words = {"not", "never", "no", "none", "cannot", "n't"}



# Cross-Encoder for contextual scoring
cross_encoder_model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/stsb-roberta-large")
cross_encoder_tokenizer = AutoTokenizer.from_pretrained("cross-encoder/stsb-roberta-large")


# -------------------------------
# Preprocessing & Negation
# -------------------------------
def preprocess_text(text: str):
    tokens = word_tokenize(text.lower())
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return " ".join(tokens)

def contains_negation(text: str):
    tokens = set(word_tokenize(text.lower()))
    return any(word in negation_words for word in tokens)


# -------------------------------
# Evaluation Function
# -------------------------------
def evaluate_answer(student_ans: str, teacher_ans: str):
    """
    Returns score (0-100), and a dict breakdown.
    Uses Hugging Face REST API for SBERT similarity and
    Cross-Encoder locally.
    """
    student = (student_ans or "").strip()
    teacher = (teacher_ans or "").strip()
    if not student:
        return 0.0, {"reason": "Empty answer"}

    try:
        student_clean = preprocess_text(student)
        teacher_clean = preprocess_text(teacher)

        # --------------------------
        # SBERT similarity via HF REST API
        # --------------------------
        import os
        import requests

        API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/sentence-similarity"
        headers = {
            "Authorization": f"Bearer {os.environ['HF_API_KEY']}",
        }

        def query(payload):
            response = requests.post(API_URL, headers=headers, json=payload)
            return response.json()

        output = query({
            "inputs": {
            "source_sentence": teacher_clean,
            "sentences": [
                student_clean,
            ]
        },
        })

        sbert_score = output[0]
        # --------------------------
        # Cross-Encoder similarity
        # --------------------------
        inputs = cross_encoder_tokenizer(student_clean, teacher_clean, return_tensors="pt", truncation=True)
        with torch.no_grad():
            logits = cross_encoder_model(**inputs).logits
        cross_score = torch.sigmoid(logits).item()

        # --------------------------
        # Negation handling
        # --------------------------
        student_neg = contains_negation(student)
        teacher_neg = contains_negation(teacher)
        if student_neg != teacher_neg:
            sbert_score *= 0.5
            cross_score *= 0.5
            negation_penalty = 0.5
        else:
            negation_penalty = 0.0

        # --------------------------
        # Final weighted score
        # --------------------------
        final = 0.4 * sbert_score + 0.6 * cross_score
        final = final * (1.0 - negation_penalty)
        final_pct = round(final * 100, 2)

        breakdown = {
            "sbert_score": round(sbert_score * 100, 2),
            "cross_score": round(cross_score * 100, 2),
            "negation_penalty": negation_penalty,
            "final_pct": final_pct
        }

        return final_pct, breakdown

    except Exception as e:
        logger.exception("Evaluation failed")
        return 0.0, {"error": str(e)}
