"""Lay-language -> GDPR-terminology expansion for queries.

Each rule: a regex over the lower-cased question and the legal terms to append. Deliberately
small, readable and auditable (a compliance system should be able to explain why a query was
rewritten). Rules come from the regulation's own vocabulary (definitions in Article 4, article
titles, recurring phrasing), not from individual test questions; the held-out set checks that.
"""
import re

RULES = [
    # who
    (r"\b(compan(y|ies)|business(es)?|organi[sz]ations?|firms?|employers?|we|our|us)\b", "controller"),
    (r"\b(vendors?|suppliers?|service providers?|outsourc\w*|cloud|third[- ]party (provider|vendor))\b", "processor on behalf of the controller"),
    (r"\b(customers?|users?|people|persons?|individuals?|someone|patients?|consumers?|employees?|my data|their data)\b", "data subject"),
    (r"\b(regulators?|authorit(y|ies)|watchdog|data protection authorit\w+|dpas?)\b", "supervisory authority"),
    (r"\b(dpo|data protection officer)\b", "data protection officer designation"),
    (r"\bchild(ren)?|teen\w*|minors?|kids?|under 1[3-8]|young\b", "child information society services parental responsibility"),
    # territory
    (r"\b(outside (of )?the (eu|european union|union|eea)|non[- ]eu|foreign|based in (?!the (eu|union))[a-z]+|overseas|brazil|india|china)\b",
     "not established in the Union controller or processor not established in the Union offering goods or services monitoring behaviour"),
    (r"\b(abroad|other countries|another country|international|outside europe|united states|(to|in) the (us|usa)|third countr\w+|send (data|it) outside|transfers?)\b",
     "transfer to a third country or international organisation adequacy decision appropriate safeguards"),
    # data and processing
    (r"\b(personal (information|details)|private (data|information))\b", "personal data"),
    (r"\b(health|medical|religio\w*|ethnic\w*|racial|political|sexual|biometric|genetic|trade union|criminal)\b", "special categories of personal data"),
    (r"\banonymi[sz]\w*|pseudonym\w*\b", "anonymous information pseudonymisation additional information"),
    (r"\b(profiling|algorithm\w*|automated|automatic decisions?|ai decision\w*)\b", "automated individual decision-making profiling legal effects"),
    (r"\b(marketing|advertis\w+|newsletters?)\b", "direct marketing right to object"),
    (r"\b(employees?|workers?|staff|workplace|at work)\b", "processing in the context of employment"),
    (r"\b(journalis\w+|press|media|artistic|academic)\b", "freedom of expression and information journalistic purposes"),
    (r"\b(research|statistic\w*|archiv\w+)\b", "scientific or historical research purposes statistical purposes archiving"),
    # legal grounds and consent
    (r"\b(legal (basis|bases|grounds?)|lawful\w*|allowed to (use|process)|permitted)\b", "lawfulness of processing"),
    (r"\b(agree|agreement|opt[- ]in|permission|withdr\w+)\b", "consent conditions for consent"),
    (r"\b(legitimate|our own business interest)\b", "legitimate interests"),
    # rights
    (r"\b(delet\w+|remov\w+|erase\w*|forgotten|wipe)\b", "erasure right to erasure right to be forgotten"),
    (r"\b(copy of|see (my|their|the) data|access to (my|their|the) data|what data .* (hold|have))\b", "right of access by the data subject"),
    (r"\b(correct\w*|fix\w*|incorrect|inaccurate|wrong data|update)\b", "rectification inaccurate personal data"),
    (r"\b(port\w+|move (my|their|the) data|another (service|provider)|machine[- ]readable)\b", "right to data portability structured commonly used machine-readable format"),
    (r"\b(object\w*|stop (using|processing)|opt[- ]out)\b", "right to object"),
    (r"\b(restrict\w*|pause|freeze|suspend)\b", "restriction of processing"),
    (r"\b(tell|informed|informing|notice|notif\w+|transparen\w+|privacy (policy|notice))\b", "information to be provided transparency"),
    # security / breach / assessments
    (r"\b(breach\w*|hack\w*|leak\w*|stolen|lost data|data loss|cyber ?attack|ransomware|security incident)\b", "personal data breach notification to the supervisory authority within 72 hours communication to the data subject"),
    (r"\b(security|secure|encrypt\w*|protect\w*|safeguard\w*)\b", "security of processing appropriate technical and organisational measures"),
    (r"\b(risk assessment|impact assessment|dpia|high risk|large[- ]scale|systematic monitoring)\b", "data protection impact assessment"),
    (r"\b(records?|register|documentation|document\w*)\b", "records of processing activities"),
    (r"\b(by design|by default|privacy by design)\b", "data protection by design and by default"),
    # enforcement
    (r"\b(fines?|penalt\w+|sanctions?|punish\w*)\b", "administrative fines infringement"),
    (r"\b(complain\w*)\b", "right to lodge a complaint with a supervisory authority"),
    (r"\b(court|sue|lawsuit|judicial|appeal)\b", "right to an effective judicial remedy"),
    (r"\b(compensat\w+|damages?|liable|liability)\b", "right to compensation and liability"),
    (r"\b(powers?|investigat\w+|audit\w*|corrective)\b", "powers of the supervisory authority investigative corrective"),
    (r"\b(lead authority|several (eu )?countries|multiple (eu )?countries|one[- ]stop)\b", "lead supervisory authority cross-border processing main establishment"),
    (r"\b(certificat\w+|seal|code of conduct|codes of conduct)\b", "certification codes of conduct"),
    (r"\b(corporate rules|bcrs?|standard (contractual )?clauses|scc)\b", "binding corporate rules standard data protection clauses"),
]
_COMPILED = [(re.compile(p), terms) for p, terms in RULES]


def expand(question):
    """Return (terms, matched rule indexes). Whole phrases are appended; exact duplicates removed."""
    q = question.lower()
    phrases, hits = [], []
    for i, (rx, add) in enumerate(_COMPILED):
        if rx.search(q):
            hits.append(i)
            if add not in phrases:
                phrases.append(add)
    return "; ".join(phrases), hits


def expanded_query(question, style="append"):
    terms, _ = expand(question)
    if not terms:
        return question
    return f"{question} ({terms})" if style == "append" else terms
