from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def analyze_grouped_answers(grouped_data):

    insights = {}

    for question, entries in grouped_data.items():
        answers = [entry["answer"] for entry in entries]
        total_responses = len(answers)
        all_text = " ".join(answers).lower()
        words = all_text.split()
        common_words = Counter(words).most_common(5)
        
        # ---- TF-IDF SIMILARITY ----
        if len(answers) > 1:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(answers)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            avg_similarity = similarity_matrix.mean()
        else:
            avg_similarity = 0.0
        
        # ---- FREQUENT ANSWERS ----
        answer_counts = Counter(answers)
        frequent_answers = [
            ans for ans, count in answer_counts.items() if count > 1
        ]
        
        # ---- QUESTION DIFFICULTY ----
        difficulty = calculate_difficulty(answers, avg_similarity)
        
        # ---- COMMON MISTAKES ----
        common_mistakes = detect_common_mistakes(entries)
        
        insights[question] = {
            "total_responses": total_responses,
            "common_words": common_words,
            "avg_similarity": round(float(avg_similarity), 2),
            "frequent_answers": frequent_answers,
            "difficulty": difficulty,
            "common_mistakes": common_mistakes,
        }

    return insights


def calculate_difficulty(answers, avg_similarity):
    """Calculate question difficulty based on answer quality and similarity"""
    avg_length = np.mean([len(a.split()) for a in answers]) if answers else 0
    unique_ratio = len(set(" ".join(answers).split())) / max(len(" ".join(answers).split()), 1)
    
    difficulty_score = (avg_length / 20) * 0.4 + (unique_ratio) * 0.3 + (1 - avg_similarity) * 0.3
    
    if difficulty_score > 0.6:
        return "Hard"
    elif difficulty_score > 0.35:
        return "Medium"
    else:
        return "Easy"


def detect_common_mistakes(entries):
    """Detect common mistakes in student answers"""
    mistakes = []
    
    error_patterns = {
        "short_answer": lambda a: len(a.split()) <= 3,
        "no_content": lambda a: a.strip().lower() in ["", "n/a", "none", "idk", "don't know"],
        "incomplete": lambda a: not a.endswith(".") and len(a.split()) < 5,
    }
    
    for pattern_name, check_func in error_patterns.items():
        count = sum(1 for e in entries if check_func(e["answer"]))
        if count > 0:
            mistakes.append({
                "type": pattern_name,
                "count": count,
                "percentage": round(count / len(entries) * 100, 1)
            })
    
    return mistakes


def identify_strong_weak_students(grouped_data, insights, clusters, weak_concepts):
    """Identify strong vs weak students based on their answers"""
    student_scores = {}
    
    for question, entries in grouped_data.items():
        for entry in entries:
            student_id = entry["student_id"]
            student_name = entry["student_name"]
            answer = entry["answer"]
            
            if student_id not in student_scores:
                student_scores[student_id] = {
                    "name": student_name,
                    "scores": [],
                    "answer_lengths": [],
                    "is_unique": []
                }
            
            score = 0
            answer_length = len(answer.split())
            student_scores[student_id]["answer_lengths"].append(answer_length)
            
            if answer_length >= 10:
                score += 30
            elif answer_length >= 5:
                score += 20
            else:
                score += 5
            
            if answer_length <= 4:
                score -= 10
            
            if insights[question]["frequent_answers"]:
                is_common = answer in insights[question]["frequent_answers"]
                student_scores[student_id]["is_unique"].append(not is_common)
                if not is_common:
                    score += 20
            
            student_scores[student_id]["scores"].append(score)
    
    strong_students = []
    weak_students = []
    average_students = []
    
    for student_id, data in student_scores.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        
        student_data = {
            "student_id": student_id,
            "name": data["name"],
            "avg_score": round(avg_score, 1),
            "avg_answer_length": round(sum(data["answer_lengths"]) / len(data["answer_lengths"]) if data["answer_lengths"] else 0, 1)
        }
        
        if avg_score >= 40:
            strong_students.append(student_data)
        elif avg_score <= 20:
            weak_students.append(student_data)
        else:
            average_students.append(student_data)
    
    strong_students.sort(key=lambda x: x["avg_score"], reverse=True)
    weak_students.sort(key=lambda x: x["avg_score"])
    average_students.sort(key=lambda x: x["avg_score"], reverse=True)
    
    return {
        "strong": strong_students[:10],
        "weak": weak_students[:10],
        "average": average_students
    }


def detect_conceptual_errors(grouped_data, clusters):
    """Detect repeated conceptual errors across students"""
    conceptual_errors = []
    
    for question, entries in grouped_data.items():
        error_answers = []
        for entry in entries:
            answer_lower = entry["answer"].lower()
            if any(neg in answer_lower for neg in ["don't", "does not", "not sure", "i think"]):
                if len(entry["answer"].split()) > 5:
                    error_answers.append({
                        "student_id": entry["student_id"],
                        "student_name": entry["student_name"],
                        "answer": entry["answer"],
                        "issue": "Uncertain/correct answer"
                    })
        
        if error_answers:
            conceptual_errors.append({
                "question": question,
                "count": len(error_answers),
                "answers": error_answers[:3]
            })
    
    return conceptual_errors
