"""
Explainability Module
Provides transparency in AI output - explains why insights were generated
"""

def explain_cluster_selection(cluster, all_answers, threshold=0.3):
    """
    Explain why answers were grouped in a cluster
    
    Args:
        cluster: List of answers in the cluster
        all_answers: All student answers
        threshold: Similarity threshold
    
    Returns:
        Explanation dictionary
    """
    cluster_size = len(cluster)
    total_answers = len(all_answers)
    
    # Calculate what percentage of class shares this answer pattern
    percentage = round((cluster_size / total_answers) * 100, 1) if total_answers > 0 else 0
    
    # Determine if this is a common or rare pattern
    if percentage > 40:
        classification = "Highly Common"
        explanation = "This answer pattern is shared by a large portion of the class."
    elif percentage > 20:
        classification = "Moderately Common"
        explanation = "Several students shared this answer pattern."
    else:
        classification = "Less Common"
        explanation = "Fewer students shared this answer pattern."
    
    return {
        'cluster_size': cluster_size,
        'class_percentage': percentage,
        'classification': classification,
        'explanation': explanation,
        'sample_answers': cluster[:3] if len(cluster) > 3 else cluster
    }


def explain_weak_concept(concept_type, count, total, threshold_ratio=0.2):
    """
    Explain why a concept was flagged as weak
    
    Args:
        concept_type: Type of weak concept ('short_answers', 'low_vocab')
        count: Number of students with this issue
        total: Total number of students
        threshold_ratio: Threshold for flagging
    
    Returns:
        Explanation dictionary
    """
    percentage = round((count / total) * 100, 1) if total > 0 else 0
    is_flagged = percentage > (threshold_ratio * 100)
    
    if concept_type == 'short_answers':
        if is_flagged:
            explanation = f"{count} students ({percentage}%) gave answers with 4 or fewer words. This may indicate shallow understanding or rushing."
            severity = "high" if percentage > 40 else "medium"
        else:
            explanation = "Most students provided adequate-length answers."
            severity = "low"
    elif concept_type == 'low_vocab':
        if is_flagged:
            explanation = f"Students showed limited vocabulary diversity ({percentage}% unique words). This may indicate need for vocabulary building."
            severity = "medium"
        else:
            explanation = "Students showed good vocabulary diversity."
            severity = "low"
    else:
        explanation = "Concept analysis complete."
        severity = "low"
    
    return {
        'concept_type': concept_type,
        'count': count,
        'total': total,
        'percentage': percentage,
        'is_flagged': is_flagged,
        'explanation': explanation,
        'severity': severity
    }


def explain_similarity_score(similarity_score):
    """
    Explain what a similarity score means
    
    Args:
        similarity_score: TF-IDF similarity score (0-1)
    
    Returns:
        Explanation dictionary
    """
    score_percentage = round(similarity_score * 100, 1)
    
    if similarity_score > 0.6:
        interpretation = "High Similarity"
        meaning = "Students gave very similar answers - either due to memorization or clear understanding of the concept."
        confidence = "High"
    elif similarity_score > 0.3:
        interpretation = "Moderate Similarity"
        meaning = "Students showed variation in their answers with some common patterns."
        confidence = "Medium"
    else:
        interpretation = "Low Similarity"
        meaning = "Students gave diverse answers - may indicate confusion or unique interpretations."
        confidence = "Medium"
    
    return {
        'score': similarity_score,
        'score_percentage': score_percentage,
        'interpretation': interpretation,
        'meaning': meaning,
        'confidence': confidence
    }


def explain_insight_score(insight_score, confidence_score):
    """
    Explain the insight and confidence scores
    
    Args:
        insight_score: AI-generated insight score
        confidence_score: Confidence in the analysis
    
    Returns:
        Explanation dictionary
    """
    # Insight score explanation
    if insight_score >= 75:
        insight_meaning = "High understanding detected. Students demonstrated clear grasp of the concept."
        insight_reliability = "Reliable"
    elif insight_score >= 50:
        insight_meaning = "Moderate understanding. Some students grasp the concept, others may need help."
        insight_reliability = "Moderately Reliable"
    else:
        insight_meaning = "Low understanding. Significant review and re-teaching may be needed."
        insight_reliability = "Less Reliable - small sample or diverse answers"
    
    # Confidence score explanation
    if confidence_score >= 70:
        confidence_meaning = "High confidence in analysis due to sufficient data."
        data_adequacy = "Adequate"
    elif confidence_score >= 40:
        confidence_meaning = "Moderate confidence. More data would improve accuracy."
        data_adequacy = "Partial"
    else:
        confidence_meaning = "Low confidence. Limited data may affect accuracy."
        data_adequacy = "Insufficient"
    
    return {
        'insight_score': insight_score,
        'insight_meaning': insight_meaning,
        'insight_reliability': insight_reliability,
        'confidence_score': confidence_score,
        'confidence_meaning': confidence_meaning,
        'data_adequacy': data_adequacy
    }


def generate_transparency_report(question, insights, clusters, weak_concepts, scores):
    """
    Generate a complete transparency report for a question
    
    Args:
        question: Question ID
        insights: Insights data
        clusters: Cluster data
        weak_concepts: Weak concepts
        scores: Calculated scores
    
    Returns:
        Complete transparency report
    """
    report = {
        'question_id': question,
        'total_responses': insights.get('total_responses', 0),
        'similarity_analysis': explain_similarity_score(insights.get('avg_similarity', 0)),
        'score_explanation': explain_insight_score(
            scores.get('insight_score', 0),
            scores.get('confidence_score', 0)
        ),
        'cluster_explanations': [],
        'weak_concept_explanations': []
    }
    
    # Explain each cluster
    if clusters:
        for i, cluster in enumerate(clusters):
            cluster_exp = explain_cluster_selection(
                cluster,
                insights.get('frequent_answers', []) + [c for c_list in clusters for c in c_list]
            )
            cluster_exp['cluster_id'] = i + 1
            report['cluster_explanations'].append(cluster_exp)
    
    # Explain weak concepts
    if weak_concepts:
        total = insights.get('total_responses', 1)
        for concept_type, count in weak_concepts.items():
            if isinstance(count, int):
                report['weak_concept_explanations'].append(
                    explain_weak_concept(concept_type, count, total)
                )
    
    return report
