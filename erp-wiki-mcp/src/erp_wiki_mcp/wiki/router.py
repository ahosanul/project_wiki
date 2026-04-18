"""Intent router for question classification."""

import re


def classify_intent(question: str) -> str:
    """
    Classify question into intent category.
    
    Returns one of: Location | Logic | Impact | Trace | Relation | Discovery
    Default: Logic
    """
    q = question.lower()
    
    # Location patterns
    location_patterns = [
        r"where is",
        r"which file",
        r"find the",
        r"where does",
        r"location of",
        r"file for",
    ]
    for pattern in location_patterns:
        if re.search(pattern, q):
            return "Location"
    
    # Impact patterns
    impact_patterns = [
        r"what calls",
        r"who uses",
        r"what breaks if",
        r"callers of",
        r"impact of changing",
        r"dependents of",
    ]
    for pattern in impact_patterns:
        if re.search(pattern, q):
            return "Impact"
    
    # Trace patterns
    trace_patterns = [
        r"trace",
        r"follow",
        r"from request to",
        r"end to end",
        r"flow of",
        r"request flow",
        r"execution path",
    ]
    for pattern in trace_patterns:
        if re.search(pattern, q):
            return "Trace"
    
    # Relation patterns
    relation_patterns = [
        r"what injects",
        r"what renders",
        r"what does .* use",
        r"depends on",
        r"relationship between",
        r"connected to",
    ]
    for pattern in relation_patterns:
        if re.search(pattern, q):
            return "Relation"
    
    # Discovery patterns
    discovery_patterns = [
        r"list all",
        r"show all",
        r"what controllers",
        r"what services",
        r"what domains",
        r"how many",
        r"enumerate",
    ]
    for pattern in discovery_patterns:
        if re.search(pattern, q):
            return "Discovery"
    
    # Logic patterns (also default)
    logic_patterns = [
        r"how does",
        r"what does",
        r"explain",
        r"walk me through",
        r"describe",
        r"how it works",
    ]
    for pattern in logic_patterns:
        if re.search(pattern, q):
            return "Logic"
    
    return "Logic"
