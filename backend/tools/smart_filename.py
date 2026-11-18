"""
Smart Report Filename Generator
================================
Extracts meaningful keywords from research topics to create clean filenames.

Instead of: "Research_the_implications_of_AGI_and_superintelligence_on_global_economic_systems_and_the_future_of_humanity.pdf"
Produces:   "AGI_Superintelligence_Economics_20260115.pdf"

Usage:
    from backend.tools.smart_filename import generate_smart_filename
    
    filename = generate_smart_filename("Research AGI and its economic implications")
    # Returns: "AGI_Economic_Implications_20260115"
"""

import re
from datetime import datetime
from typing import List, Optional


# Stopwords to remove (common filler words)
STOPWORDS = {
    # Articles
    "a", "an", "the",
    # Prepositions
    "of", "on", "in", "at", "to", "for", "with", "by", "from", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "against", "among",
    # Conjunctions
    "and", "or", "but", "nor", "so", "yet",
    # Common verbs
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they",
    "this", "that", "these", "those",
    # Common prompt words
    "research", "study", "analyze", "investigate", "explore", "examine",
    "explain", "describe", "discuss", "review", "generate", "create",
    "write", "produce", "professional", "phd", "level", "paper",
    "report", "comprehensive", "detailed", "thorough", "deep",
    # Misc
    "how", "what", "why", "when", "where", "which", "who",
    "please", "need", "want", "help", "me", "my", "your",
}

# Important domain keywords to boost (never filter these)
DOMAIN_KEYWORDS = {
    # AI/ML
    "ai", "agi", "ml", "llm", "gpt", "transformer", "neural", "deep",
    "machine", "learning", "artificial", "intelligence", "superintelligence",
    # Science
    "quantum", "biology", "physics", "chemistry", "genomics", "neuroscience",
    "protein", "folding", "crispr", "gene", "dna", "rna",
    # Tech
    "blockchain", "crypto", "web3", "cloud", "kubernetes", "docker",
    "api", "microservices", "saas", "devops", "cicd",
    # Economics/Business
    "economic", "economics", "market", "finance", "investment", "startup",
    # Misc important
    "future", "impact", "implications", "breakthrough", "revolution",
}


def generate_smart_filename(
    topic: str,
    max_keywords: int = 4,
    max_length: int = 60,
    include_date: bool = True,
    date_format: str = "%Y%m%d"
) -> str:
    """
    Generate a clean, keyword-based filename from a research topic.
    
    Args:
        topic: Full research topic or prompt
        max_keywords: Maximum number of keywords to include (default 4)
        max_length: Maximum filename length (default 60)
        include_date: Whether to append date (default True)
        date_format: Date format string (default YYYYMMDD)
        
    Returns:
        Clean filename string (without extension)
    """
    if not topic:
        return f"Research_Report_{datetime.now().strftime(date_format)}"
    
    # If topic is a dict or something else, convert it to a string representation
    if isinstance(topic, dict):
        topic = topic.get('topic', '') or topic.get('title', '') or str(topic)
    elif not isinstance(topic, str):
        topic = str(topic)
        
    # 1. Remove common prompt prefixes
    prefixes_to_remove = [
        r"^generate a professional phd level research paper on\s*",
        r"^write a detailed report on\s*",
        r"^research\s+",
        r"^analyze\s+",
        r"^investigate\s+",
        r"^explain\s+",
        r"^study\s+",
    ]
    cleaned = topic.lower()
    for prefix in prefixes_to_remove:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE)
    
    # 2. Extract words (alphanumeric only)
    words = re.findall(r'[a-zA-Z0-9]+', cleaned)
    
    # 3. Score and rank words
    scored_words = []
    for word in words:
        word_lower = word.lower()
        
        # Skip stopwords (unless it's a domain keyword)
        if word_lower in STOPWORDS and word_lower not in DOMAIN_KEYWORDS:
            continue
        
        # Skip very short words
        if len(word) <= 2:
            continue
        
        # Score: domain keywords get bonus
        score = 0
        if word_lower in DOMAIN_KEYWORDS:
            score += 10  # High priority
        score += len(word)  # Longer words = more specific
        
        scored_words.append((word.capitalize(), score))
    
    # 4. Sort by score (descending) and take top keywords
    scored_words.sort(key=lambda x: x[1], reverse=True)
    keywords = [w[0] for w in scored_words[:max_keywords]]
    
    # 5. If no keywords extracted, use first few meaningful words
    if not keywords:
        fallback_words = [w.capitalize() for w in words if len(w) > 3][:3]
        keywords = fallback_words if fallback_words else ["Research", "Report"]
    
    # 6. Build filename
    filename = "_".join(keywords)
    
    # 7. Add date if requested
    if include_date:
        date_str = datetime.now().strftime(date_format)
        filename = f"{filename}_{date_str}"
    
    # 8. Ensure Windows-safe characters only
    filename = re.sub(r'[<>:"/\\|?*\n\r]', '', filename)
    
    # 9. Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip("_")
    
    return filename


def extract_keywords(topic: str, max_count: int = 5) -> List[str]:
    """
    Extract just the keywords from a topic (for display/metadata).
    
    Args:
        topic: Research topic
        max_count: Maximum keywords to return
        
    Returns:
        List of keyword strings
    """
    if not topic:
        return []
        
    # If topic is a dict or something else, convert it to a string representation
    if isinstance(topic, dict):
        topic = str(topic.get('topic', '')) or str(topic.get('title', '')) or str(topic)
    elif not isinstance(topic, str):
        topic = str(topic)
    
    words = re.findall(r'[a-zA-Z0-9]+', topic.lower())
    
    keywords = []
    for word in words:
        word_lower = word.lower()
        if word_lower in STOPWORDS and word_lower not in DOMAIN_KEYWORDS:
            continue
        if len(word) <= 2:
            continue
        keywords.append(word.capitalize())
    
    return keywords[:max_count]


# Quick test
if __name__ == "__main__":
    test_topics = [
        "Research the implications of AGI and superintelligence on global economic systems",
        "Generate a professional PhD level research paper on quantum computing",
        "Analyze the impact of CRISPR gene editing on future medicine",
        "Deep learning neural networks for natural language processing",
        "Study blockchain cryptocurrency and Web3 technologies",
    ]
    
    print("Smart Filename Generator Test")
    print("=" * 60)
    for topic in test_topics:
        filename = generate_smart_filename(topic)
        print(f"\nTopic: {topic[:50]}...")
        print(f"Filename: {filename}")
