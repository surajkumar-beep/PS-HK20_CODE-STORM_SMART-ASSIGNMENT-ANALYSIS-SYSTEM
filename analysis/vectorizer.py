from sklearn.feature_extraction.text import TfidfVectorizer

def vectorize_answers(answers):
    vectorizer = TfidfVectorizer(stop_words='english')
    vectors = vectorizer.fit_transform(answers)
    return vectors
