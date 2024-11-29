
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class Task(BaseModel):
    project_name: str = Field(description="Name of the project.")
    task_name: str = Field(..., description="Name of the task.")
    status: str = Field(default="Not Started")#, description="Current status of the task.")
    due_date: Optional[date] = Field(..., description="Due date for the task in ISO 8601 format (YYYY-MM-DD).")
    new_task: bool = Field(description="Indicates if this is a new task.")

class ProjectOutput(BaseModel):
    project_id: Optional[str] = Field(description="Id of the project of existing project.") 
    project_name: str = Field(description="Name of the project.")
    summary: str = Field(description="Brief description or summary of the project.")
    new_project: bool = Field(description="Indicates if this is a new project.")