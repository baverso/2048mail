#!/usr/bin/env python3
"""
models.py

This script contains the Pydantic models used for parsing and validating outputs
from the various LLM agents in the EVQLV AI Email Management System.

Author: Brett Averso
Date: March 15, 2025
License: GPL-3.0
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator

# Define Pydantic models for JSON parsing
class NeedsResponseOutput(BaseModel):
    needs_response: str = Field(description="Whether the email needs a response: 'respond' or 'no response needed'")

    # Add validation for the needs_response field
    @field_validator('needs_response')
    @classmethod
    def validate_needs_response(cls, v):
        valid_values = ['respond', 'no response needed']
        if v.lower().strip() not in valid_values:
            raise ValueError(f"needs_response must be one of {valid_values}")
        return v.lower().strip()

class EmailSummaryOutput(BaseModel):
    from_field: str = Field(description="The name and organization of the email sender", alias="from")
    subject: str = Field(description="The subject line of the email")
    date: str = Field(description="The date the email was sent")
    key_points: List[str] = Field(description="An array of strings summarizing the main points from the email")
    requests_action_items: List[str] = Field(description="An array of strings detailing any explicit requests or actions required")
    context: Optional[str] = Field(description="If the email is part of a conversation, a brief summary of the related email chain", default="")
    sentiment: str = Field(description="A brief sentiment analysis of the email")

    model_config = {
        "populate_by_name": True
    }

class EmailCategoryOutput(BaseModel):
    category: str = Field(description="The category of the email: 'respond', 'decline', or other")

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        v = v.lower().strip()
        # Allow flexibility in categories but ensure common ones are standardized
        if v in ['decline', 'reject', 'refuse']:
            return 'decline'
        return v

class MeetingRequestOutput(BaseModel):
    is_meeting_request: str = Field(description="Whether the email is a meeting request: 'yes' or 'no'")
    decision: Optional[str] = Field(None, description="The decision from the meeting request prompt: 'schedule meeting' or 'other email'")

    @model_validator(mode='after')
    def map_decision_to_is_meeting_request(self):
        # If decision is provided but is_meeting_request is empty, map it
        if self.decision is not None and not self.is_meeting_request:
            if self.decision.lower().strip() == 'schedule meeting':
                self.is_meeting_request = 'yes'
            else:
                self.is_meeting_request = 'no'
        
        return self

    @field_validator('is_meeting_request')
    @classmethod
    def validate_meeting_request(cls, v):
        v = v.lower().strip()
        if v in ['yes', 'true', '1']:
            return 'yes'
        elif v in ['no', 'false', '0']:
            return 'no'
        raise ValueError("is_meeting_request must be 'yes' or 'no'")

class SpecificChange(BaseModel):
    type: str = Field(description="The type of change (e.g., 'Addition', 'Deletion', 'Rewording', 'Tone shift', 'Structure')")
    original: str = Field(description="The original text or a description of what was in the draft")
    edited: str = Field(description="The edited text or a description of what replaced it")
    likely_reason: str = Field(description="The inferred reason for this change")

class EditorAnalysisOutput(BaseModel):
    changes_summary: str = Field(description="A brief overview of the types of changes made")
    specific_changes: List[SpecificChange] = Field(description="An array of specific changes identified")
    inferred_preferences: List[str] = Field(description="An array of preferences that can be inferred from the edits")
    recommendations: List[str] = Field(description="Actionable recommendations for future email drafting") 