"""
Feedback Generator Module
Generates student-level and class-level feedback drafts
"""

def generate_student_feedback(student_data, question_insights, clusters, weak_concepts):
    """
    Generate individualized feedback for a student
    
    Args:
        student_data: Dictionary with student info and their answers
        question_insights: Insights for each question
        clusters: Answer clusters
        weak_concepts: Weak concepts detected
    
    Returns:
        Dictionary with feedback for each question
    """
    feedback = {}
    
    for q_id, answer in student_data.get('answers', {}).items():
        insights = question_insights.get(q_id, {})
        
        # Determine if answer matches common patterns
        is_common = answer in insights.get('frequent_answers', [])
        
        # Check answer similarity
        avg_sim = insights.get('avg_similarity', 0)
        
        # Generate feedback based on analysis
        if avg_sim > 0.6:
            pattern_status = "common answer pattern"
            suggestion = "Your answer follows the common pattern observed in class."
        elif avg_sim > 0.3:
            pattern_status = "moderate variation"
            suggestion = "Your answer shows some variation from the common pattern."
        else:
            pattern_status = "unique perspective"
            suggestion = "Your answer provides a unique perspective."
        
        feedback[q_id] = {
            'answer': answer,
            'pattern_status': pattern_status,
            'suggestion': suggestion,
            'is_common': is_common,
            'total_responses': insights.get('total_responses', 0),
            'class_avg_similarity': round(avg_sim * 100, 1)
        }
    
    return feedback


def generate_class_feedback(grouped_data, insights, clusters, weak_concepts, scores):
    """
    Generate class-level feedback summary
    
    Args:
        grouped_data: Grouped student answers by question
        insights: Analysis insights
        clusters: Answer clusters
        weak_concepts: Weak concepts
        scores: Calculated scores
    
    Returns:
        Dictionary with class-level feedback
    """
    class_feedback = {}
    
    for q_id in grouped_data.keys():
        insights_q = insights.get(q_id, {})
        clusters_q = clusters.get(q_id, {})
        weak_q = weak_concepts.get(q_id, {})
        score_q = scores.get(q_id, {})
        
        # Calculate class performance
        understanding = score_q.get('insight_score', 0)
        confidence = score_q.get('confidence_score', 0)
        risk = score_q.get('risk_level', 'Low')
        
        # Generate teaching points
        teaching_points = []
        
        if weak_q.get('short_answers', 0) > 0:
            teaching_points.append(
                f"{weak_q['short_answers']} students gave short answers - encourage detailed explanations"
            )
        
        if weak_q.get('low_vocab_diversity', False):
            teaching_points.append(
                "Limited vocabulary diversity observed - consider vocabulary-building activities"
            )
        
        if insights_q.get('frequent_answers'):
            teaching_points.append(
                f"{len(insights_q['frequent_answers'])} common answer patterns detected"
            )
        
        # Overall recommendation
        if understanding >= 75:
            recommendation = "Class shows strong understanding. Proceed to next topic with minor reinforcement."
        elif understanding >= 50:
            recommendation = "Moderate understanding. Review key concepts with examples."
        else:
            recommendation = "Review required. Consider re-teaching with guided practice."
        
        class_feedback[q_id] = {
            'question': grouped_data[q_id][0].get('question_text', f'Question {q_id}'),
            'total_responses': insights_q.get('total_responses', 0),
            'understanding_level': score_q.get('understanding_level', 'Unknown'),
            'risk_level': risk,
            'recommendation': recommendation,
            'teaching_points': teaching_points,
            'avg_similarity': round(insights_q.get('avg_similarity', 0) * 100, 1),
            'common_keywords': [w for w, c in insights_q.get('common_words', [])[:5]],
            'clusters_count': len(clusters_q)
        }
    
    return class_feedback


def generate_improvement_suggestions(weak_concepts, insights):
    """
    Generate improvement suggestions based on weak concepts
    
    Args:
        weak_concepts: Dictionary of weak concepts per question
        insights: Insights data
    
    Returns:
        List of improvement suggestions
    """
    suggestions = []
    
    total_short = sum(w.get('short_answers', 0) for w in weak_concepts.values())
    total_low_vocab = sum(1 for w in weak_concepts.values() if w.get('low_vocab_diversity', False))
    
    if total_short > 0:
        suggestions.append({
            'type': 'answer_length',
            'priority': 'high' if total_short > 5 else 'medium',
            'message': f"{total_short} students submitted short answers. Encourage more detailed responses."
        })
    
    if total_low_vocab > 0:
        suggestions.append({
            'type': 'vocabulary',
            'priority': 'medium',
            'message': "Some students show limited vocabulary. Consider vocabulary-building exercises."
        })
    
    # Check for repeated answers
    for q_id, insight in insights.items():
        if insight.get('frequent_answers'):
            suggestions.append({
                'type': 'common_patterns',
                'priority': 'low',
                'message': f"Q{q_id}: {len(insight['frequent_answers'])} repeated answers found."
            })
    
    return suggestions
