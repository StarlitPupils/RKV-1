"""Private frozen-method proposal, tiny owned text only; no science scoring."""
from collections import Counter
from rkv1.experiments.paper_retriever import tokens


def select_indices(question, sentences, *, method):
    if type(question) is not str or not question.strip() or type(sentences) is not list or any(type(s) is not str for s in sentences):
        raise ValueError('Question and original sentence strings required')
    if method not in ('first_two', 'overlap_two'):
        raise ValueError('Explicit proposed method required')
    if method == 'first_two':
        return list(range(min(2, len(sentences))))
    query = Counter(tokens(question))
    scored = []
    for index, sentence in enumerate(sentences):
        words = Counter(tokens(sentence))
        score = sum(min(count, words[word]) for word, count in query.items())
        scored.append((-score, index))
    # Fixed multiset token intersection; original index resolves ties.
    # Restore original source order after choosing, for faithful citation mapping.
    return sorted(index for _, index in sorted(scored)[:2])
