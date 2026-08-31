from typing import Any

def extract_technologies(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract technologies from repository metadata.
    Returns a list of dicts: {"name": str, "confidence": float}
    """
    technologies = []
    
    # 1. Direct language mapping
    language = metadata.get("language")
    if language:
        technologies.append({"name": language.strip().lower(), "confidence": 1.0})
        
    # 2. Topic tags
    topics = metadata.get("topics", [])
    for topic in topics:
        name = topic.strip().lower()
        if name:
            technologies.append({"name": name, "confidence": 1.0})
        
    # 3. File signals
    files = metadata.get("files", [])
    files_lower = [f.lower() for f in files]
    
    if "dockerfile" in files_lower:
        technologies.append({"name": "docker", "confidence": 0.7})
        
    if "helm" in files_lower or "charts" in files_lower:
        technologies.append({"name": "kubernetes", "confidence": 0.7})
        
    if "go.mod" in files_lower:
        technologies.append({"name": "go", "confidence": 0.7})
        
    if "requirements.txt" in files_lower or "pyproject.toml" in files_lower:
        technologies.append({"name": "python", "confidence": 0.7})
        
    if "package.json" in files_lower:
        technologies.append({"name": "node.js", "confidence": 0.7})
        
    # Deduplicate, keeping highest confidence
    deduped = {}
    for tech in technologies:
        name = tech["name"]
        if name not in deduped or tech["confidence"] > deduped[name]:
            deduped[name] = tech["confidence"]
            
    return [{"name": name, "confidence": conf} for name, conf in deduped.items()]
