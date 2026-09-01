"""Canonical technology names — aliases collapse before clustering and trends."""

from __future__ import annotations

# alias (lowercase) -> canonical key (lowercase, stable for grouping)
ALIAS_TO_KEY: dict[str, str] = {
    "go": "go",
    "golang": "go",
    "node.js": "node.js",
    "nodejs": "node.js",
    "javascript": "javascript",
    "typescript": "typescript",
    "python": "python",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "helm": "helm",
    "terraform": "terraform",
    "ai": "ai-agents",
    "llm": "ai-agents",
    "llms": "ai-agents",
    "agents": "ai-agents",
    "agent": "ai-agents",
    "ai-agent": "ai-agents",
    "ai-agents": "ai-agents",
    "agentic": "ai-agents",
    "agentic-ai": "ai-agents",
    "agentic-systems": "ai-agents",
    "machine learning": "machine-learning",
    "machine-learning": "machine-learning",
    "ml": "machine-learning",
    "pytorch": "machine-learning",
    "inference": "inference",
    "vllm": "inference",
    "opentelemetry": "opentelemetry",
    "prometheus": "prometheus",
    "automation": "automation",
    "cli": "cli",
    "devtools": "devtools",
}

DISPLAY_NAME: dict[str, str] = {
    "go": "Go",
    "node.js": "Node.js",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "helm": "Helm",
    "terraform": "Terraform",
    "ai-agents": "AI Agents",
    "machine-learning": "Machine Learning",
    "inference": "Inference",
    "opentelemetry": "OpenTelemetry",
    "prometheus": "Prometheus",
    "automation": "Automation",
    "cli": "CLI",
    "devtools": "DevTools",
}


def canonical_key(name: str) -> str:
    raw = (name or "").strip().lower()
    if not raw:
        return raw
    if raw in ALIAS_TO_KEY:
        return ALIAS_TO_KEY[raw]
    for alias, key in ALIAS_TO_KEY.items():
        if alias in raw or raw in alias:
            return key
    return raw


def display_name(name: str) -> str:
    key = canonical_key(name)
    return DISPLAY_NAME.get(key, key[:1].upper() + key[1:] if key else name)


def canonicalize_tech(name: str) -> tuple[str, str]:
    """Return (canonical_key, display_name)."""
    key = canonical_key(name)
    return key, DISPLAY_NAME.get(key, display_name(name))
