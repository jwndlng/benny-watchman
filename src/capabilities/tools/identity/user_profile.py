"""UserProfile schema returned by the lookup_user tool."""

from datetime import date

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Identity and employment context returned by the lookup_user tool."""

    name: str = Field(description="Full name")
    email: str = Field(description="Work email")
    team: str = Field(description="Team or department")
    role: str = Field(description="Job title / role")
    manager: str = Field(description="Direct manager")
    employment_status: str = Field(description="active | on_leave | terminated")
    start_date: date = Field(description="Employment start date")
    termination_date: date | None = Field(description="Scheduled termination date if known")
    tenure_days: int = Field(description="Number of days employed as of today")
    work_location: str = Field(description="Primary office location or 'remote'")
    timezone: str = Field(description="Work timezone")
    on_call: bool = Field(description="Currently on call")
    out_of_office: bool = Field(description="Currently OOO")
    access_level: str = Field(description="Expected privilege level for this role")
