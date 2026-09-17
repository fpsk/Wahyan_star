"""
Open Knowledge Format (OKF) 0.2 Schema Definitions
Structured Pydantic Models for Historical Yearbook Entity Extraction,
Source Grounding, and Knowledge Graph Construction.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TextSpanEvidence(BaseModel):
    """Source text span evidence for zero-hallucination verification."""
    text: str = Field(..., description="The exact text snippet as printed in the source document.")
    start_char: Optional[int] = Field(None, description="Starting character index in the source text.")
    end_char: Optional[int] = Field(None, description="Ending character index in the source text.")


class StudentRosterEntry(BaseModel):
    """Individual student entry in a class roster or graduation list."""
    english_name: str = Field(..., description="Student's English name (e.g. Luk Hoi Tak, Poon Sek Kwong).")
    chinese_name: Optional[str] = Field("", description="Student's Traditional Chinese name if present (e.g. 陸海德, 潘錫光).")
    class_designation: Optional[str] = Field(None, description="Form/Class (e.g. Form 1A, Form 2B1, Form 3B1, Lower 6 Arts).")
    seat_number: Optional[int] = Field(None, description="Class seat or roll number if numbered.")
    is_prefect: bool = Field(False, description="Whether the student is marked as a prefect or class monitor.")
    is_graduate: bool = Field(False, description="Whether the student is marked as a Form 5 or Form 6 graduate.")
    evidence: Optional[TextSpanEvidence] = Field(None, description="Direct text grounding evidence.")


class StaffDirectoryEntry(BaseModel):
    """Faculty, clergy, administrative, or pastoral staff member."""
    english_name: str = Field(..., description="Staff member's English name (e.g. Fr. J. Barrett, S.J., Mr. Raymond Yu).")
    chinese_name: Optional[str] = Field("", description="Traditional Chinese name if present (e.g. 余本良).")
    title_or_role: str = Field(..., description="Role (e.g. Rector, Principal, Vice-Principal, Form Master, Subject Teacher, Counsellor).")
    department_or_subject: Optional[str] = Field("", description="Academic subject taught or administrative department.")
    speech_or_report_title: Optional[str] = Field(None, description="Title of speech or annual report authored on this page.")
    evidence: Optional[TextSpanEvidence] = Field(None, description="Source grounding evidence.")


class ClubActivityEntry(BaseModel):
    """Extracurricular club, society, or committee entry."""
    club_name: str = Field(..., description="Name of club/society (e.g. Debating Society, Judo Club, Science Society, St. John Ambulance).")
    event_or_activity: Optional[str] = Field(None, description="Specific event, trip, exhibition, or competition.")
    participant_name_en: str = Field(..., description="Participant or officer English name.")
    participant_name_zh: Optional[str] = Field("", description="Participant or officer Chinese name.")
    role: Optional[str] = Field("Member", description="Role in club (e.g. Chairman, Secretary, Treasurer, Committee Member, Conductor).")
    evidence: Optional[TextSpanEvidence] = Field(None, description="Source grounding evidence.")


class SportsRecordEntry(BaseModel):
    """Athletic meet, swimming gala, or inter-school tournament record."""
    event_name: str = Field(..., description="Event name (e.g. 100m Freestyle, High Jump, Tennis Singles, Inter-House Relay).")
    category_or_grade: Optional[str] = Field(None, description="Grade category (e.g. Grade A, Grade B, Open, Inter-Class).")
    athlete_name_en: str = Field(..., description="Athlete English name (e.g. Lee Chi, Yau Kai Hong).")
    athlete_name_zh: Optional[str] = Field("", description="Athlete Chinese name if present.")
    record_or_time: Optional[str] = Field(None, description="Recorded time, distance, or score (e.g. 1:04.2, 5.82m).")
    is_school_record: bool = Field(False, description="Whether marked as a new school record or record breaker.")
    rank_or_place: Optional[int] = Field(None, description="Finishing place (1 for 1st/Champion, 2 for 2nd, etc.).")
    evidence: Optional[TextSpanEvidence] = Field(None, description="Source grounding evidence.")


class OKFPageV2(BaseModel):
    """Comprehensive OKF 0.2 Structured Page Representation."""
    year: str = Field(..., description="Year or volume identifier (e.g. 1971, 1973, 1975_F5_Alumni).")
    page: int = Field(..., description="Page number.")
    section_type: str = Field(
        "General",
        description="Primary section type: 'Class Roster', 'Staff Directory', 'Clubs & Societies', 'Sports & Athletics', 'Principal Speech', 'Articles & Literature', 'Advertisements', 'Photos & Gallery'."
    )
    class_designation: Optional[str] = Field(None, description="Specific Class designation if page is a roster (e.g. Form 3B1).")
    summary: str = Field(..., description="Concise bilingual or English summary of page contents.")
    
    # Structured Entity Collections
    students: List[StudentRosterEntry] = Field(default_factory=list, description="All students identified on this page.")
    staff: List[StaffDirectoryEntry] = Field(default_factory=list, description="All staff/faculty identified on this page.")
    activities: List[ClubActivityEntry] = Field(default_factory=list, description="All club/society records.")
    sports_records: List[SportsRecordEntry] = Field(default_factory=list, description="All athletic & swimming records.")
    
    # Associated media assets
    full_page_photo: Optional[str] = Field(None, description="Filename of 300 DPI full page scan.")
    extracted_photos: List[str] = Field(default_factory=list, description="List of cropped photo filenames.")
