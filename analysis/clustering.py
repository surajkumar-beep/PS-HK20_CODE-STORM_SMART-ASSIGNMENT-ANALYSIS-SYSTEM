from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np


def cluster_answers(answers, max_clusters=5):
    """
    Groups similar answers using TF-IDF + KMeans
    Always returns multiple clusters when possible
    """

    if len(answers) < 2:
        return []

    # If all answers are identical, return as single cluster
    if len(set(answers)) == 1:
        return [answers]

    vectorizer = TfidfVectorizer(stop_words="english")
    
    try:
        X = vectorizer.fit_transform(answers)
    except ValueError:
        # If vectorization fails, return single cluster
        return [answers]

    # Calculate optimal number of clusters based on data
    unique_answers = len(set(answers))
    n_clusters = min(max_clusters, unique_answers, len(answers))
    
    # Ensure at least 2 clusters if possible
    if n_clusters < 2:
        return [answers]

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)

    # Build clusters
    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(answers[idx])

    # If only 1 cluster, try with fewer clusters or return all
    if len(clusters) == 1:
        # Split the single cluster into smaller groups based on similarity
        return split_into_groups(answers, max_clusters)
    
    return list(clusters.values())


def split_into_groups(answers, max_groups=3):
    """
    Split answers into groups when they're all similar
    """
    if len(answers) <= max_groups:
        return [[ans] for ans in answers]
    
    # Split evenly
    group_size = len(answers) // max_groups
    groups = []
    for i in range(max_groups):
        start = i * group_size
        if i == max_groups - 1:
            groups.append(answers[start:])
        else:
            groups.append(answers[start:start + group_size])
    
    return [g for g in groups if g]


def detect_weak_concepts(answers):
    """
    Simple heuristics to detect weak understanding
    """

    weak_signals = {}

    # Short answers → shallow understanding
    short_answers = [a for a in answers if len(a.split()) <= 4]
    weak_signals["short_answers"] = len(short_answers)

    # Vocabulary diversity
    all_words = " ".join(answers).split()
    unique_ratio = len(set(all_words)) / max(len(all_words), 1)

    weak_signals["low_vocab_diversity"] = unique_ratio < 0.4

    return weak_signals
