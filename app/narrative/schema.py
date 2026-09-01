from pydantic import BaseModel


class WeeklyNarrative(BaseModel):
    headline: str = ""                          # 1-line attention grabber
    narrative: str                              # 1-3 sentence summary
    why_it_matters: str | None = None           # grounded interpretation
    technologies_mentioned: list[str]
    supporting_event_ids: list[int]
    focus_area: str | None = None               # e.g. "observability", "infrastructure"
    activity_type: str | None = None            # e.g. "external_contribution", "release"
