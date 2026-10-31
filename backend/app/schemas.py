from typing import Literal

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    repo_url: str


class CreateRunResponse(BaseModel):
    run_id: str


class Section(BaseModel):
    key: str
    title: str
    markdown: str


class FirstIssue(BaseModel):
    number: int
    title: str
    url: str
    reason: str
    difficulty: Literal["easy", "medium", "hard"]


class Report(BaseModel):
    repo: str
    summary: str
    sections: list[Section]
    mermaid: str
    first_issues: list[FirstIssue]