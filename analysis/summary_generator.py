def generate_structured_summary(question_id, insights, clusters, weak_concepts, scores):

    total = insights["total_responses"]
    similarity = insights["avg_similarity"]
    insight_score = scores["insight_score"]
    confidence_score = scores["confidence_score"]
    short_answers = weak_concepts["short_answers"]

    # ---- Understanding Level ----
    if insight_score >= 75:
        understanding_level = "High"
    elif insight_score >= 50:
        understanding_level = "Moderate"
    else:
        understanding_level = "Low"

    # ---- Pattern Type ----
    if similarity > 0.6:
        pattern_type = "Highly similar responses (possible memorization or clear understanding)"
    elif similarity > 0.3:
        pattern_type = "Moderate variation in answers"
    else:
        pattern_type = "Highly diverse responses (concept confusion possible)"

    # ---- Risk Level ----
    if short_answers > total * 0.4:
        risk_level = "High"
    elif short_answers > total * 0.2:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # ---- Teaching Action ----
    if understanding_level == "Low":
        teaching_action = "Re-teach the concept with examples and guided practice."
    elif risk_level == "High":
        teaching_action = "Focus on encouraging detailed explanations and deeper thinking."
    else:
        teaching_action = "Minor clarification and reinforcement recommended."

    # ---- Final Summary Text ----
    summary_text = (
        f"For Question {question_id}, the overall understanding level is {understanding_level}. "
        f"Responses show {pattern_type}. "
        f"The detected risk level is {risk_level}. "
        f"Recommended action: {teaching_action}"
    )

    return {
        "understanding_level": understanding_level,
        "pattern_type": pattern_type,
        "risk_level": risk_level,
        "teaching_action": teaching_action,
        "summary_text": summary_text
    }