from pydantic import BaseModel, Field

class WeeklyNarrative(BaseModel):
    narrative: str = Field(description="1-3 plain sentences describing the week's activity.")
    technologies_mentioned: list[str] = Field(description="List of technologies explicitly mentioned.")
    supporting_event_ids: list[int] = Field(description="List of event IDs that support the narrative facts.")
