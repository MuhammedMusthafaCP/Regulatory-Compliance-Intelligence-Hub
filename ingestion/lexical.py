"""In-process BM25 over the chunk texts (the lexical half of hybrid search).

Postgres full-text ranking has no IDF weighting, so ubiquitous GDPR words ("data", "processing")
would add noise; BM25 down-weights them. 670 chunks make an in-memory index trivial.
"""
import math
import re
from collections import Counter

import snowballstemmer

_stem = snowballstemmer.stemmer("english").stemWord
STOP = frozenset("""a about above after again all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its itself just me more most my no nor not of off on once only or other our out over own same she should so some
such than that the their them then there these they this those through to too under until up very was we were what when where which
while who whom why will with would you your yours""".split())


def tokenize(text):
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = sum(self.len) / len(docs)
        df = Counter(w for t in self.tf for w in t)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def scores(self, query):
        """BM25 score of every document for the query (0 where no query term matches)."""
        q = [w for w in tokenize(query) if w in self.idf]
        out = []
        for tf, ln in zip(self.tf, self.len):
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / self.avg))
            out.append(s)
        return out
