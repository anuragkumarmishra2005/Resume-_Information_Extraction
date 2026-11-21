"""Data models representing structured resume information.

Conforms strictly to the project target JSON schema.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PersonalLinks(BaseModel):
    """Links associated with the candidate."""
    linkedin: Optional[str] = None
    github: Optional[str] = None
    other: List[str] = Field(default_factory=list)


class PersonalData(BaseModel):
    """Personal and contact information."""
    name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    links: PersonalLinks = Field(default_factory=PersonalLinks)


class SkillsData(BaseModel):
    """Categorized and aggregated skills."""
    all: List[str] = Field(default_factory=list)
    by_category: Dict[str, List[str]] = Field(default_factory=dict)


class EducationItem(BaseModel):
    """Single educational background item."""
    degree: Optional[str] = None
    institution: Optional[str] = None
    location: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None


class ExperienceItem(BaseModel):
    """Single work experience or employment item."""
    title: Optional[str] = None
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    description: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """Single project item."""
    name: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    description: List[str] = Field(default_factory=list)


class MetaData(BaseModel):
    """Document extraction metadata and diagnostic warnings."""
    source_file: str = ""
    pages: int = 1
    extraction_time_ms: int = 0
    warnings: List[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    """Root model for all structured resume data."""
    personal: PersonalData = Field(default_factory=PersonalData)
    summary: Optional[str] = None
    skills: SkillsData = Field(default_factory=SkillsData)
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    meta: MetaData = Field(default_factory=MetaData)

    def to_dict(self) -> dict:
        """Export to dictionary conforming to the target JSON schema."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string conforming to the target JSON schema."""
        return self.model_dump_json(indent=indent)
