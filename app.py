import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from processing.parser import parse_csv, parse_json, parse_excel, parse_pdf, group_by_question
from analysis.insights import analyze_grouped_answers, identify_strong_weak_students, detect_conceptual_errors
from analysis.clustering import cluster_answers, detect_weak_concepts
from analysis.summary_generator import generate_structured_summary
from feedback.feedback_generator import generate_student_feedback, generate_class_feedback, generate_improvement_suggestions
from feedback.explainability import generate_transparency_report
from feedback.pdf_generator import create_pdf_report, generate_text_report, create_excel_report

from auth.routes import auth_bp
from db.database import init_db


# ============ HELPER FUNCTIONS FOR FILE-BASED STORAGE ============

def save_analysis_to_file(data):
    """Save analysis data to a temporary file"""
    analysis_id = str(uuid.uuid4())
    filepath = os.path.join('exports', 'feedback_reports', f'analysis_{analysis_id}.json')
    
    # Convert non-serializable objects to serializable format
    serializable_data = make_serializable(data)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f)
    
    return analysis_id

def make_serializable(obj):
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, (set, tuple)):
        return list(obj)
    else:
        return obj

def load_analysis_from_file(analysis_id):
    """Load analysis data from file"""
    filepath = os.path.join('exports', 'feedback_reports', f'analysis_{analysis_id}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# Ensure exports directory exists
os.makedirs('exports/feedback_reports', exist_ok=True)

init_db()
app.register_blueprint(auth_bp)


# ---------------- helper ----------------

def login_required():
    return "teacher_id" in session


# ---------------- ROOT (/) ----------------

@app.route("/")
def home():
    if login_required():
        return redirect(url_for("index"))
    return redirect(url_for("auth.login"))


# ---------------- INDEX PAGE ----------------

@app.route("/index")
def index():
    if not login_required():
        return redirect(url_for("auth.login"))
    return render_template(
        "index.html",
        teacher_name=session.get("teacher_name")
    )


# ---------- score calculation function ----------

def calculate_scores(question, insights, clusters, weak_concepts):
    total = insights["total_responses"]
    avg_similarity = insights["avg_similarity"]
    short_answers = weak_concepts["short_answers"]
    low_vocab = weak_concepts["low_vocab_diversity"]

    vocab_score = 0 if low_vocab else 1
    length_score = 1 - (short_answers / total if total else 0)

    insight_score = (
        avg_similarity * 40 +
        vocab_score * 20 +
        length_score * 20 +
        20
    )

    insight_score = round(min(insight_score, 100), 2)
    confidence_score = min(100, total * 10 + len(clusters) * 15)

    return insight_score, confidence_score


# ---------------- UPLOAD ----------------

@app.route("/upload", methods=["POST"])
def upload():
    if not login_required():
        return redirect(url_for("auth.login"))

    file = request.files.get("file")

    if not file:
        return render_template("index.html", error="No file selected")

    # Support multiple formats: CSV, JSON, Excel
    if file.filename.endswith(".csv"):
        data = parse_csv(file)
    elif file.filename.endswith(".json"):
        data = parse_json(file)
    elif file.filename.endswith(".xlsx"):
        data = parse_excel(file)
    elif file.filename.endswith(".pdf"):
        data = parse_pdf(file)
    else:
        return render_template("index.html", error="Invalid file format. Please upload CSV, JSON, Excel (.xlsx), or PDF files.")

    grouped_data = group_by_question(data)
    insights = analyze_grouped_answers(grouped_data)

    # Calculate total students
    all_students = set()
    for rows in grouped_data.values():
        for row in rows:
            all_students.add(row["student_id"])
    total_students = len(all_students)

    # Calculate overall average similarity
    if insights:
        overall_avg_similarity = round(
            sum(i["avg_similarity"] for i in insights.values()) / len(insights), 2
        )
    else:
        overall_avg_similarity = 0

    clusters = {}
    weak_concepts = {}
    scores = {}
    summaries = {}
    transparency_reports = {}
    student_feedback = {}

    # Group data by student for individual feedback
    student_data = {}
    for q_id, rows in grouped_data.items():
        for row in rows:
            student_id = row["student_id"]
            if student_id not in student_data:
                student_data[student_id] = {
                    "student_id": student_id,
                    "student_name": row["student_name"],
                    "answers": {}
                }
            student_data[student_id]["answers"][q_id] = row["answer"]

    for q, rows in grouped_data.items():
        ans = [r["answer"] for r in rows]

        clusters[q] = cluster_answers(ans)
        weak_concepts[q] = detect_weak_concepts(ans)

        i, c = calculate_scores(
            q,
            insights[q],
            clusters[q],
            weak_concepts[q]
        )

        scores[q] = {
            "insight_score": i,
            "confidence_score": c
        }

        summaries[q] = generate_structured_summary(
            q,
            insights[q],
            clusters[q],
            weak_concepts[q],
            scores[q]
        )

        # Add understanding and risk level to scores
        scores[q]["understanding_level"] = summaries[q]["understanding_level"]
        scores[q]["risk_level"] = summaries[q]["risk_level"]

        # Generate transparency report for explainability
        transparency_reports[q] = generate_transparency_report(
            q, insights[q], clusters[q], weak_concepts[q], scores[q]
        )

    # Generate student-level feedback
    for student_id, s_data in student_data.items():
        student_feedback[student_id] = generate_student_feedback(
            s_data, insights, clusters, weak_concepts
        )

    # Generate class-level feedback
    class_feedback = generate_class_feedback(
        grouped_data, insights, clusters, weak_concepts, scores
    )

    # Generate improvement suggestions
    improvement_suggestions = generate_improvement_suggestions(weak_concepts, insights)

    # NEW: Identify strong vs weak students
    student_classification = identify_strong_weak_students(grouped_data, insights, clusters, weak_concepts)

    # NEW: Detect conceptual errors
    conceptual_errors = detect_conceptual_errors(grouped_data, clusters)

    # NEW: Calculate similarity distribution for chart
    similarity_high = sum(1 for i in insights.values() if i['avg_similarity'] > 0.6)
    similarity_medium = sum(1 for i in insights.values() if 0.3 < i['avg_similarity'] <= 0.6)
    similarity_low = sum(1 for i in insights.values() if i['avg_similarity'] <= 0.3)

    # Store data in file for large datasets
    analysis_data = {
        'grouped_data': grouped_data,
        'insights': insights,
        'clusters': clusters,
        'weak_concepts': weak_concepts,
        'scores': scores,
        'summaries': summaries,
        'total_students': total_students,
        'overall_avg_similarity': overall_avg_similarity,
        'transparency_reports': transparency_reports,
        'student_feedback': student_feedback,
        'class_feedback': class_feedback,
        'improvement_suggestions': improvement_suggestions,
        'student_classification': student_classification,
        'conceptual_errors': conceptual_errors,
        'similarity_distribution': {
            'high': similarity_high,
            'medium': similarity_medium,
            'low': similarity_low
        }
    }
    
    # Save to file and store only the ID in session
    analysis_id = save_analysis_to_file(analysis_data)
    session['analysis_id'] = analysis_id

    return render_template(
        "dashboard.html",
        grouped_data=grouped_data,
        insights=insights,
        clusters=clusters,
        weak_concepts=weak_concepts,
        scores=scores,
        summaries=summaries,
        teacher_name=session["teacher_name"],
        total_students=total_students,
        overall_avg_similarity=overall_avg_similarity,
        transparency_reports=transparency_reports,
        student_feedback=student_feedback,
        class_feedback=class_feedback,
        improvement_suggestions=improvement_suggestions,
        student_classification=student_classification,
        conceptual_errors=conceptual_errors,
        similarity_distribution={
            'high': similarity_high,
            'medium': similarity_medium,
            'low': similarity_low
        }
    )


# ---------------- EXPORT PDF ----------------

@app.route("/export_pdf")
def export_pdf():
    if not login_required():
        return redirect(url_for("auth.login"))

    # Load data from file instead of session
    analysis_id = session.get('analysis_id')
    if not analysis_id:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    data = load_analysis_from_file(analysis_id)
    if not data:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    # Prepare data for PDF
    pdf_data = {
        'overall_summary': {
            'total_students': data['total_students'],
            'total_questions': len(data['grouped_data']),
            'overall_similarity': data['overall_avg_similarity'],
            'avg_insight_score': round(
                sum(s['insight_score'] for s in data['scores'].values()) / len(data['scores']), 2
            ) if data['scores'] else 0
        },
        'questions': {}
    }

    for q_id in data['grouped_data'].keys():
        pdf_data['questions'][q_id] = {
            'question_text': data['grouped_data'][q_id][0].get('question_text', ''),
            'total_responses': data['insights'][q_id]['total_responses'],
            'insight_score': data['scores'][q_id]['insight_score'],
            'confidence_score': data['scores'][q_id]['confidence_score'],
            'understanding_level': data['scores'][q_id]['understanding_level'],
            'risk_level': data['scores'][q_id]['risk_level'],
            'teaching_action': data['summaries'][q_id]['teaching_action'],
            'common_keywords': [w for w, c in data['insights'][q_id].get('common_words', [])[:5]],
            'weak_concepts': data['weak_concepts'][q_id]
        }

    # Generate filename
    from datetime import datetime
    filename = f"assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join('exports/feedback_reports', filename)

    # Create PDF
    create_pdf_report(pdf_data, output_path, session['teacher_name'])

    return send_file(output_path, as_attachment=True, download_name=filename)


# ---------------- EXPORT TEXT ----------------

@app.route("/export_text")
def export_text():
    if not login_required():
        return redirect(url_for("auth.login"))

    # Load data from file instead of session
    analysis_id = session.get('analysis_id')
    if not analysis_id:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    data = load_analysis_from_file(analysis_id)
    if not data:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    # Prepare data for text report
    text_data = {
        'overall_summary': {
            'total_students': data['total_students'],
            'total_questions': len(data['grouped_data']),
            'overall_similarity': data['overall_avg_similarity'],
            'avg_insight_score': round(
                sum(s['insight_score'] for s in data['scores'].values()) / len(data['scores']), 2
            ) if data['scores'] else 0
        },
        'questions': {}
    }

    for q_id in data['grouped_data'].keys():
        text_data['questions'][q_id] = {
            'question_text': data['grouped_data'][q_id][0].get('question_text', ''),
            'total_responses': data['insights'][q_id]['total_responses'],
            'insight_score': data['scores'][q_id]['insight_score'],
            'confidence_score': data['scores'][q_id]['confidence_score'],
            'understanding_level': data['scores'][q_id]['understanding_level'],
            'risk_level': data['scores'][q_id]['risk_level'],
            'teaching_action': data['summaries'][q_id]['teaching_action'],
            'common_keywords': [w for w, c in data['insights'][q_id].get('common_words', [])[:5]],
            'weak_concepts': data['weak_concepts'][q_id]
        }

    # Generate filename
    from datetime import datetime
    filename = f"assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path = os.path.join('exports/feedback_reports', filename)

    # Create text report
    generate_text_report(text_data, output_path, session['teacher_name'])

    return send_file(output_path, as_attachment=True, download_name=filename)


# ---------------- EXPORT EXCEL ----------------

@app.route("/export_excel")
def export_excel():
    if not login_required():
        return redirect(url_for("auth.login"))

    # Load data from file instead of session
    analysis_id = session.get('analysis_id')
    if not analysis_id:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    data = load_analysis_from_file(analysis_id)
    if not data:
        flash("No analysis data to export")
        return redirect(url_for("index"))

    # Prepare data for Excel
    excel_data = {
        'overall_summary': {
            'total_students': data['total_students'],
            'total_questions': len(data['grouped_data']),
            'overall_similarity': data['overall_avg_similarity'],
            'avg_insight_score': round(
                sum(s['insight_score'] for s in data['scores'].values()) / len(data['scores']), 2
            ) if data['scores'] else 0
        },
        'questions': {}
    }

    for q_id in data['grouped_data'].keys():
        excel_data['questions'][q_id] = {
            'question_text': data['grouped_data'][q_id][0].get('question_text', ''),
            'total_responses': data['insights'][q_id]['total_responses'],
            'insight_score': data['scores'][q_id]['insight_score'],
            'confidence_score': data['scores'][q_id]['confidence_score'],
            'understanding_level': data['scores'][q_id]['understanding_level'],
            'risk_level': data['scores'][q_id]['risk_level'],
            'teaching_action': data['summaries'][q_id]['teaching_action'],
            'common_keywords': [w for w, c in data['insights'][q_id].get('common_words', [])[:5]],
            'weak_concepts': data['weak_concepts'][q_id]
        }

    # Generate filename
    from datetime import datetime
    filename = f"assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = os.path.join('exports/feedback_reports', filename)

    # Create Excel report
    create_excel_report(excel_data, output_path, session['teacher_name'])

    return send_file(output_path, as_attachment=True, download_name=filename)


# ---------------- SAVE FEEDBACK (EDIT/APPROVE) ----------------

@app.route("/save_feedback", methods=["POST"])
def save_feedback():
    if not login_required():
        return jsonify({"success": False, "error": "Not logged in"})

    analysis_id = session.get('analysis_id')
    if not analysis_id:
        return jsonify({"success": False, "error": "No analysis data"})

    data = load_analysis_from_file(analysis_id)
    if not data:
        return jsonify({"success": False, "error": "No analysis data"})

    request_data = request.get_json()
    question_id = request_data.get('question_id')
    new_feedback = request_data.get('feedback')

    if question_id and new_feedback:
        # Update data
        data['summaries'][question_id]['teaching_action'] = new_feedback
        
        # Save back to file
        save_analysis_to_file(data)
        
        return jsonify({"success": True, "message": "Feedback updated successfully"})

    return jsonify({"success": False, "error": "Invalid data"})


# ---------------- GET TRANSPARENCY DATA ----------------

@app.route("/get_transparency/<question_id>")
def get_transparency(question_id):
    if not login_required():
        return jsonify({"error": "Not logged in"})

    analysis_id = session.get('analysis_id')
    if not analysis_id:
        return jsonify({"error": "No analysis data"})

    data = load_analysis_from_file(analysis_id)
    if not data:
        return jsonify({"error": "No analysis data"})

    transparency = data.get('transparency_reports', {}).get(question_id)
    if transparency:
        return jsonify(transparency)
    return jsonify({"error": "Data not found"})


if __name__ == "__main__":
    app.run(debug=True)
