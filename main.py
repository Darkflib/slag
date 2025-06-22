"""
SLAG Commenting System - FastAPI Backend
A commenting system based on storing JSON files in a directory structure.
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, UUID4, field_validator
from rich import print

# Configure application
app = FastAPI(
    title="SLAG Commenting System",
    description="API for managing comments stored in JSON files",
    version="0.1.0",
)

# Define the directory where comment files will be stored
COMMENTS_DIR = Path("comments")
COMMENTS_DIR.mkdir(exist_ok=True)


# Pydantic models for validation
class CommentFlags(BaseModel):
    hidden: bool = False
    moderated: bool = False
    reported: bool = False
    deleted: bool = False


class Comment(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author: str
    datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    text: str
    parent: Optional[str] = None
    flags: CommentFlags = Field(default_factory=CommentFlags)
    
    @field_validator("datetime")
    def validate_datetime(cls, v):
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Invalid datetime format. Must be ISO 8601 format.")


class CommentThread(BaseModel):
    page_id: str
    comments: List[Comment] = []


class CommentCreate(BaseModel):
    author: str
    text: str


class CommentUpdate(BaseModel):
    author: Optional[str] = None
    text: Optional[str] = None
    flags: Optional[CommentFlags] = None


# Helper functions
def get_comment_file_path(page_id: str) -> Path:
    """Get the path to a comment file based on page_id."""
    return COMMENTS_DIR / f"{page_id}.json"


def load_comment_thread(page_id: str) -> CommentThread:
    """Load a comment thread from a JSON file."""
    file_path = get_comment_file_path(page_id)
    
    if not file_path.exists():
        # Return an empty comment thread if the file doesn't exist
        return CommentThread(page_id=page_id, comments=[])
    
    try:
        data = json.loads(file_path.read_text())
        return CommentThread(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[bold red]Error loading comment thread:[/bold red] {e}")
        # If the file is corrupted, return an empty thread
        return CommentThread(page_id=page_id, comments=[])


def save_comment_thread(thread: CommentThread) -> None:
    """Save a comment thread to a JSON file."""
    file_path = get_comment_file_path(thread.page_id)
    file_path.write_text(thread.model_dump_json(indent=2))


# API Endpoints
@app.get("/")
def read_root():
    """Root endpoint with basic information about the API."""
    return {
        "name": "SLAG Commenting System",
        "version": "0.1.0",
        "description": "API for managing comments stored in JSON files",
        "endpoints": [
            "GET /comments/{page_id}",
            "POST /comments/{page_id}",
            "PUT /comments/{page_id}/{comment_uuid}",
            "DELETE /comments/{page_id}/{comment_uuid}",
            "GET /comments/{page_id}/replies/{parent_uuid}",
            "POST /comments/{page_id}/replies/{parent_uuid}",
            "PUT /comments/{page_id}/replies/{parent_uuid}/{reply_uuid}",
            "DELETE /comments/{page_id}/replies/{parent_uuid}/{reply_uuid}"
        ]
    }


@app.get("/comments/{page_id}")
def get_comments(page_id: str):
    """Retrieve all comments for a specific page."""
    thread = load_comment_thread(page_id)
    # Filter out replies (comments with parent) to return only top-level comments
    return {
        "page_id": page_id,
        "comments": [comment for comment in thread.comments if comment.parent is None]
    }


@app.post("/comments/{page_id}", status_code=status.HTTP_201_CREATED)
def create_comment(page_id: str, comment_data: CommentCreate):
    """Create a new comment on a specific page."""
    thread = load_comment_thread(page_id)
    
    # Create a new comment
    new_comment = Comment(
        author=comment_data.author,
        text=comment_data.text
    )
    
    thread.comments.append(new_comment)
    save_comment_thread(thread)
    
    return new_comment


@app.put("/comments/{page_id}/{comment_uuid}")
def update_comment(page_id: str, comment_uuid: str, comment_data: CommentUpdate):
    """Update an existing comment."""
    thread = load_comment_thread(page_id)
    
    # Find the comment
    for i, comment in enumerate(thread.comments):
        if comment.uuid == comment_uuid:
            # Update the comment fields
            if comment_data.author is not None:
                comment.author = comment_data.author
            if comment_data.text is not None:
                comment.text = comment_data.text
            if comment_data.flags is not None:
                comment.flags = comment_data.flags
            
            thread.comments[i] = comment
            save_comment_thread(thread)
            return comment
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Comment with UUID {comment_uuid} not found"
    )


@app.delete("/comments/{page_id}/{comment_uuid}")
def delete_comment(page_id: str, comment_uuid: str):
    """Delete a comment by UUID."""
    thread = load_comment_thread(page_id)
    
    # Find the comment
    for i, comment in enumerate(thread.comments):
        if comment.uuid == comment_uuid:
            # Remove the comment
            deleted_comment = thread.comments.pop(i)
            
            # Also remove any replies to this comment
            thread.comments = [c for c in thread.comments if c.parent != comment_uuid]
            
            save_comment_thread(thread)
            return {"detail": "Comment deleted successfully", "comment": deleted_comment}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Comment with UUID {comment_uuid} not found"
    )


@app.get("/comments/{page_id}/replies/{parent_uuid}")
def get_replies(page_id: str, parent_uuid: str):
    """Retrieve all replies to a specific comment."""
    thread = load_comment_thread(page_id)
    
    # Filter out only replies to the specified parent
    replies = [comment for comment in thread.comments if comment.parent == parent_uuid]
    
    return {
        "page_id": page_id,
        "parent_uuid": parent_uuid,
        "replies": replies
    }


@app.post("/comments/{page_id}/replies/{parent_uuid}", status_code=status.HTTP_201_CREATED)
def create_reply(page_id: str, parent_uuid: str, comment_data: CommentCreate):
    """Create a new reply to a specific comment."""
    thread = load_comment_thread(page_id)
    
    # Check if parent comment exists
    parent_exists = any(comment.uuid == parent_uuid for comment in thread.comments)
    if not parent_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent comment with UUID {parent_uuid} not found"
        )
    
    # Create a new reply
    new_reply = Comment(
        author=comment_data.author,
        text=comment_data.text,
        parent=parent_uuid
    )
    
    thread.comments.append(new_reply)
    save_comment_thread(thread)
    
    return new_reply


@app.put("/comments/{page_id}/replies/{parent_uuid}/{reply_uuid}")
def update_reply(page_id: str, parent_uuid: str, reply_uuid: str, comment_data: CommentUpdate):
    """Update an existing reply."""
    thread = load_comment_thread(page_id)
    
    # Find the reply
    for i, comment in enumerate(thread.comments):
        if comment.uuid == reply_uuid and comment.parent == parent_uuid:
            # Update the reply fields
            if comment_data.author is not None:
                comment.author = comment_data.author
            if comment_data.text is not None:
                comment.text = comment_data.text
            if comment_data.flags is not None:
                comment.flags = comment_data.flags
            
            thread.comments[i] = comment
            save_comment_thread(thread)
            return comment
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Reply with UUID {reply_uuid} not found for parent {parent_uuid}"
    )


@app.delete("/comments/{page_id}/replies/{parent_uuid}/{reply_uuid}")
def delete_reply(page_id: str, parent_uuid: str, reply_uuid: str):
    """Delete a reply by UUID."""
    thread = load_comment_thread(page_id)
    
    # Find the reply
    for i, comment in enumerate(thread.comments):
        if comment.uuid == reply_uuid and comment.parent == parent_uuid:
            # Remove the reply
            deleted_reply = thread.comments.pop(i)
            save_comment_thread(thread)
            return {"detail": "Reply deleted successfully", "reply": deleted_reply}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Reply with UUID {reply_uuid} not found for parent {parent_uuid}"
    )


if __name__ == "__main__":
    import uvicorn
    print("[bold green]Starting SLAG Commenting System[/bold green]")
    uvicorn.run(app, host="0.0.0.0", port=8000)
