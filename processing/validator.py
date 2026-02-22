REQUIRED_COLUMNS = {"student_id", "question", "answer"}

def validate_dataframe(df):
    if df.empty:
        return False, "Uploaded file is empty"

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return False, f"Missing required columns: {missing}"

    return True, "Valid input"
