import json
import csv
import openpyxl
from collections import defaultdict
def parse_csv(file):
    decoded = file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    if not reader.fieldnames:
        raise ValueError("Uploaded CSV file is empty")

    required_columns = {
        "student_id",
        "student_name",
        "question_id",
        "question",
        "answer"
    }
    if not required_columns.issubset(set(reader.fieldnames)):
        raise ValueError(
            f"CSV must contain columns: {required_columns}"
        )

    data = []

    for row in reader:
        if not row["answer"].strip():
            continue 

        data.append({
            "student_id": row["student_id"].strip(),
            "student_name": row["student_name"].strip(),
            "question_id": row["question_id"].strip(),
            "question": row["question"].strip(),
            "answer": row["answer"].strip()
        })

    return data

def parse_json(file):
    try:
        data = json.load(file)
    except Exception:
        raise ValueError("Invalid JSON file")

    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects")

    required_keys = {
        "student_id",
        "student_name",
        "question_id",
        "question",
        "answer"
    }

    parsed = []

    for item in data:
        if not required_keys.issubset(set(item.keys())):
            raise ValueError(
                f"Each JSON object must contain: {required_keys}"
            )

        if not item["answer"].strip():
            continue

        parsed.append({
            "student_id": str(item["student_id"]).strip(),
            "student_name": item["student_name"].strip(),
            "question_id": item["question_id"].strip(),
            "question": item["question"].strip(),
            "answer": item["answer"].strip()
        })

    return parsed

def parse_excel(file):
    """Parse Excel (.xlsx) files"""
    try:
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        
        # Get headers from first row
        headers = [cell.value for cell in sheet[1]]
        
        if not headers:
            raise ValueError("Uploaded Excel file is empty")
        
        required_columns = {
            "student_id",
            "student_name",
            "question_id",
            "question",
            "answer"
        }
        
        # Create header mapping (case-insensitive)
        header_map = {}
        for idx, header in enumerate(headers):
            if header:
                header_map[header.lower().strip()] = idx
        
        # Check required columns
        missing = []
        for col in required_columns:
            if col not in header_map:
                missing.append(col)
        
        if missing:
            raise ValueError(f"Excel must contain columns: {required_columns}")
        
        data = []
        
        # Read rows starting from second row
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or not any(row):
                continue
            
            student_id = row[header_map["student_id"]]
            student_name = row[header_map["student_name"]]
            question_id = row[header_map["question_id"]]
            question = row[header_map["question"]]
            answer = row[header_map["answer"]]
            
            # Skip empty answers
            if not answer or (isinstance(answer, str) and not answer.strip()):
                continue
            
            data.append({
                "student_id": str(student_id).strip() if student_id else "",
                "student_name": str(student_name).strip() if student_name else "",
                "question_id": str(question_id).strip() if question_id else "",
                "question": str(question).strip() if question else "",
                "answer": str(answer).strip() if answer else ""
            })
        
        return data
        
    except Exception as e:
        raise ValueError(f"Invalid Excel file: {str(e)}")


def parse_pdf(file):
    """Parse PDF files containing student assignment data using pdfminer.six"""
    try:
        from pdfminer.high_level import extract_text
        import re
        import io
        
        # Read PDF content and extract text
        pdf_content = file.read()
        pdf_file = io.BytesIO(pdf_content)
        full_text = extract_text(pdf_file)
        
        if not full_text.strip():
            raise ValueError("PDF appears to be empty or contains no extractable text")
        
        data = []
        lines = full_text.split('\n')
        
        # Strategy 1: Look for structured patterns in each line
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to extract student ID (typically a number at start or after "ID:")
            student_id_match = re.search(r'(?:^|[,\s]ID[:\s]?|student[_\s]?id[:\s]?|ID[:\s]*)(\d+)', line, re.IGNORECASE)
            if student_id_match:
                if current_entry and 'answer' in current_entry:
                    data.append(current_entry)
                current_entry = {'student_id': student_id_match.group(1)}
                continue
            
            # If we have a student_id, try to get name (usually comes after ID)
            if 'student_id' in current_entry and 'student_name' not in current_entry:
                # Look for name pattern (text without numbers, after ID or Student)
                name_match = re.search(r'(?:Name[:\s]*|Student[:\s]*)([A-Za-z\s\.]+)', line, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip()
                    if name and len(name) < 50:
                        current_entry['student_name'] = name
                        continue
            
            # Try to extract question ID (Q1, Q2, Question 1, etc.)
            question_id_match = re.search(r'(?:Q(?:uestion)?[_\s]?(?:ID)?[:\s]*|#?Q?[:\s]?)([A-Za-z0-9]+)', line, re.IGNORECASE)
            if question_id_match and 'student_id' in current_entry:
                qid = question_id_match.group(1).strip()
                if qid and qid.lower() not in ['id', 'name', 'answer']:
                    current_entry['question_id'] = qid
                    continue
            
            # Try to extract question text
            if 'question_id' in current_entry and 'question' not in current_entry:
                # Question text typically comes after "Question:" or "Q:"
                q_text_match = re.search(r'(?:Question|Q)[^:]*[:\s]*(.+?)(?:\s*Answer|\s*Ans|$)', line, re.IGNORECASE)
                if q_text_match:
                    current_entry['question'] = q_text_match.group(1).strip()
                    continue
            
            # Try to extract answer
            if 'question' in current_entry and 'answer' not in current_entry:
                ans_match = re.search(r'(?:Answer|Ans|Response)[:\s]*(.+)', line, re.IGNORECASE)
                if ans_match:
                    current_entry['answer'] = ans_match.group(1).strip()
                    continue
                
                # If no "Answer:" prefix, treat long text as answer
                if len(line) > 10 and not re.match(r'^(?:Student|Q|ID|Name|#)\s*', line, re.IGNORECASE):
                    current_entry['answer'] = line
                    continue
            
            # If we have all required fields, save the entry
            if len(current_entry) >= 5 and 'answer' in current_entry:
                data.append(current_entry)
                current_entry = {}
        
        # Don't forget the last entry
        if current_entry and len(current_entry) >= 5 and 'answer' in current_entry:
            data.append(current_entry)
        
        # Strategy 2: If no structured data found, try comma/tab separated format
        if not data:
            for line in lines:
                parts = re.split(r'[,;\t|]+', line)
                if len(parts) >= 5:
                    student_id = parts[0].strip()
                    # Check if first part looks like a student ID (numeric)
                    if student_id.isdigit() and len(student_id) <= 8:
                        try:
                            entry = {
                                'student_id': student_id,
                                'student_name': parts[1].strip(),
                                'question_id': parts[2].strip(),
                                'question': parts[3].strip(),
                                'answer': parts[4].strip()
                            }
                            if entry['answer']:
                                data.append(entry)
                        except:
                            pass
        
        # Strategy 3: Simple sequential parsing - assume PDF has Q&A in sequence
        if not data:
            # Group lines by looking for patterns
            student_counter = 1
            question_counter = 1
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip headers
                if re.match(r'^(?:student|question|answer|name|id|#)', line, re.IGNORECASE):
                    continue
                
                # If line starts with a number, it might be student ID
                if re.match(r'^\d+[\s,;]', line):
                    parts = re.split(r'[,;\t|]+', line)
                    if len(parts) >= 2:
                        # Try to parse as: ID, Name, QID, Question, Answer
                        entry = {
                            'student_id': parts[0].strip(),
                            'student_name': parts[1].strip() if len(parts) > 1 else f"Student{student_counter}",
                            'question_id': parts[2].strip() if len(parts) > 2 else str(question_counter),
                            'question': parts[3].strip() if len(parts) > 3 else f"Question {question_counter}",
                            'answer': parts[4].strip() if len(parts) > 4 else (parts[2].strip() if len(parts) > 2 else "")
                        }
                        if entry['answer']:
                            data.append(entry)
                            student_counter += 1
                            if question_counter < student_counter:
                                question_counter = student_counter
        
        if not data:
            raise ValueError(
                "Could not parse PDF data. Please ensure the PDF contains structured data "
                "with columns: student_id, student_name, question_id, question, answer"
            )
        
        return data
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {str(e)}")


def group_by_question(data):
    grouped = defaultdict(list)
    for row in data:
        question = row["question_id"]
        grouped[question].append({
            "student_id": row["student_id"],
            "student_name": row["student_name"],
            "question_text": row["question"],
            "answer": row["answer"]
        })
    return dict(grouped)
