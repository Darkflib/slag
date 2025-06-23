from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, cast, Dict, Any, TypedDict
from ulid import ULID
import json
from pathlib import Path
from datetime import datetime, timezone
import importlib.metadata
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    COMMENTS_BASE_URL: str = "https://slag.example.com/comments"
    TARGET_BASE_URL: str = "https://example.com"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }

# Load settings
settings = Settings()

app = FastAPI()

# Get version from pyproject.toml
try:
    __version__ = importlib.metadata.version("slag-commenting")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"

DATA_DIR = Path("slag-data")
COMMENTS_DIR = DATA_DIR / "comments"
TARGETS_DIR = DATA_DIR / "targets"
FLAGS_DIR = DATA_DIR / "flags"
SNAPSHOT_FILE = DATA_DIR / "snapshot.json"

try:
    COMMENTS_DIR.mkdir(parents=True, exist_ok=True)
    TARGETS_DIR.mkdir(parents=True, exist_ok=True)
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
except IOError as e:
    print(f"Error creating data directories: {str(e)}")
    # We don't raise an exception here since this is during app startup,
    # but we print the error to help with debugging

class Actor(BaseModel):
    id: HttpUrl
    name: str
    type: str = Field("Person", json_schema_extra={"frozen": True})

class CommentNote(BaseModel):
    type: str = Field("Note", frozen=True)
    id: HttpUrl
    content: str
    published: Optional[datetime]
    attributedTo: Actor
    inReplyTo: Optional[HttpUrl] = None
    target: HttpUrl

class CommentInput(BaseModel):
    content: str
    attributedTo: Actor

class FlagUpdate(BaseModel):
    hidden: Optional[bool]
    moderated: Optional[bool]
    reported: Optional[bool]
    deleted: Optional[bool]

@app.get("/comments/{target_id}")
async def get_comments(target_id: str) -> dict:
    """
    Retrieve an ActivityStreams OrderedCollection of comment URLs for a given target.
    
    Returns:
        dict: An OrderedCollection containing the total number of comments and their URLs for the specified target. If no comments exist, returns an empty collection.
    """
    index_file = TARGETS_DIR / f"{target_id}.index.json"
    if not index_file.exists():
        return {"@context": "https://www.w3.org/ns/activitystreams", "type": "OrderedCollection", "totalItems": 0, "orderedItems": []}
        
    with index_file.open() as f:
        comment_ids = json.load(f)
        
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{settings.COMMENTS_BASE_URL}/{target_id}",
        "totalItems": len(comment_ids),
        "orderedItems": [f"{settings.COMMENTS_BASE_URL}/{cid}" for cid in comment_ids]
    }

@app.post("/comments/{target_id}", response_model=CommentNote)
async def post_comment(target_id: str, input: CommentInput) -> CommentNote:
    """
    Create a new comment for the specified target and store it as a JSON-LD file.
    
    Parameters:
        target_id (str): The identifier of the target (e.g., page or resource) to which the comment is attached.
        input (CommentInput): The content and actor information for the new comment.
    
    Returns:
        CommentNote: The created comment note object, including its unique ID and metadata.
    """
    new_id = str(ULID())
    now_dt = datetime.now(timezone.utc)
    comment_url = f"{settings.COMMENTS_BASE_URL}/{new_id}"
    
    note = CommentNote(
        type="Note",
        id=cast(HttpUrl, comment_url),
        content=input.content,
        published=now_dt,
        attributedTo=input.attributedTo,
        target=cast(HttpUrl, f"{settings.TARGET_BASE_URL}/{target_id}")
    )
    
    comment_data = note.model_dump(mode='json')
    # Ensure 'Z' suffix for UTC, as per requirement
    if now_dt.tzinfo == timezone.utc:
        comment_data['published'] = now_dt.isoformat(timespec='microseconds').replace('+00:00', 'Z')
    else:
        comment_data['published'] = now_dt.isoformat(timespec='microseconds')

    try:
        comment_file = COMMENTS_DIR / f"{new_id}.jsonld"
        with comment_file.open("w") as f:
            json.dump(comment_data, f, indent=2)

        index_file = TARGETS_DIR / f"{target_id}.index.json"
        if index_file.exists():
            with index_file.open() as f:
                comment_ids = json.load(f)
        else:
            comment_ids = []

        comment_ids.append(new_id)
        with index_file.open("w") as f:
            json.dump(comment_ids, f)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save comment: {str(e)}")

    return note

@app.get("/comment/{ulid_id}", response_model=CommentNote)
async def get_comment(ulid_id: str) -> CommentNote:
    """
    Retrieve a comment by its ULID identifier.
    
    Raises a 404 error if the comment does not exist.
    
    Parameters:
        ulid_id (str): The ULID of the comment to retrieve.
    
    Returns:
        CommentNote: The comment data as a CommentNote object.
    """
    comment_file = COMMENTS_DIR / f"{ulid_id}.jsonld"
    if not comment_file.exists():
        raise HTTPException(status_code=404, detail="Comment not found")

    try:
        with comment_file.open() as f:
            comment_data = json.load(f)
            return CommentNote(**comment_data)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read comment: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid comment data: {str(e)}")

@app.patch("/comment/{ulid_id}", response_model=CommentNote)
async def edit_comment(ulid_id: str, input: CommentInput) -> CommentNote:
    """
    Update the content and attributed actor of an existing comment.
    
    Parameters:
        ulid_id (str): The ULID identifier of the comment to edit.
        input (CommentInput): The new content and actor information for the comment.    
    Returns:
        CommentNote: The updated comment.
    
    Raises:
        HTTPException: If the comment does not exist.
    """    
    comment_file = COMMENTS_DIR / f"{ulid_id}.jsonld"
    if not comment_file.exists():
        raise HTTPException(status_code=404, detail="Comment not found")

    try:
        with comment_file.open() as f:
            comment_data = json.load(f)

        comment_data['content'] = input.content
        comment_data['attributedTo'] = input.attributedTo.model_dump(mode='json')

        with comment_file.open("w") as f:
            json.dump(comment_data, f, indent=2)

        return CommentNote(**comment_data)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update comment: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid comment data: {str(e)}")

@app.post("/comment/{ulid_id}/reply", response_model=CommentNote)
async def reply_to_comment(ulid_id: str, input: CommentInput) -> CommentNote:
    """
    Create a reply to an existing comment and associate it with the same target.
    
    Parameters:
        ulid_id (str): The ULID of the parent comment to reply to.
        input (CommentInput): The content and actor information for the reply.
    
    Returns:
        CommentNote: The created reply as a CommentNote object.
    """
    parent_comment = await get_comment(ulid_id)
    target_url = parent_comment.target
    new_id = str(ULID())
    now_dt = datetime.now(timezone.utc)
    comment_url = f"{settings.COMMENTS_BASE_URL}/{new_id}"

    reply = CommentNote(        type="Note",
        id=cast(HttpUrl, comment_url),
        content=input.content,
        published=now_dt,
        attributedTo=input.attributedTo,
        inReplyTo=parent_comment.id,
        target=target_url
    )
    
    comment_data = reply.model_dump(mode='json')
    # Ensure 'Z' suffix for UTC, as per requirement
    if now_dt.tzinfo == timezone.utc:
        comment_data['published'] = now_dt.isoformat(timespec='microseconds').replace('+00:00', 'Z')
    else:
        comment_data['published'] = now_dt.isoformat(timespec='microseconds')

    try:
        comment_file = COMMENTS_DIR / f"{new_id}.jsonld"
        with comment_file.open("w") as f:
            json.dump(comment_data, f, indent=2)

        target_id = str(target_url).rsplit("/", 1)[-1]
        index_file = TARGETS_DIR / f"{target_id}.index.json"
        if index_file.exists():
            with index_file.open() as f:
                comment_ids = json.load(f)
        else:
            comment_ids = []

        comment_ids.append(new_id)
        with index_file.open("w") as f:
            json.dump(comment_ids, f)

        return reply
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save reply: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid comment data: {str(e)}")

@app.get("/comment/{ulid_id}/flags")
async def get_flags(ulid_id: str) -> Any:
    """
    Retrieve the flag data for a comment by its ULID.
    
    Returns an empty dictionary if no flag file exists for the specified comment.
    """
    flag_file = FLAGS_DIR / f"{ulid_id}.flags.json"
    if not flag_file.exists():
        return {}

    try:
        with flag_file.open() as f:
            return json.load(f)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read flags: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid flag data: {str(e)}")

@app.patch("/comment/{ulid_id}/flags")
async def update_flags(ulid_id: str, flags: FlagUpdate) -> dict:
    """
    Update the flag fields for a comment, merging new values with any existing flags.
    
    Parameters:
    	ulid_id (str): The ULID identifier of the comment.
    	flags (FlagUpdate): The flag updates to apply; only non-None values are merged.
    
    Returns:
    	dict: The updated dictionary of flag values for the comment.
    """
    flag_file = FLAGS_DIR / f"{ulid_id}.flags.json"
    existing_flags = {}
    try:
        if flag_file.exists():
            with flag_file.open() as f:
                existing_flags = json.load(f)

        updated_flags = {**existing_flags, **{k: v for k, v in flags.model_dump(mode='json').items() if v is not None}}

        with flag_file.open("w") as f:
            json.dump(updated_flags, f, indent=2)

        return updated_flags
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update flags: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid flag data: {str(e)}")

@app.post("/admin/rebuild-index")
async def rebuild_index() -> dict:
    """
    Rebuilds all target index files by scanning comment files and grouping comment ULIDs by their associated targets.
    
    Returns:
        dict: A dictionary containing the status and a list of target IDs for which indexes were rebuilt.    """
    index: Dict[str, List[str]] = {}
    try:
        for comment_file in COMMENTS_DIR.glob("*.jsonld"):
            with comment_file.open() as f:
                comment = json.load(f)
                target_id = comment['target'].rsplit("/", 1)[-1]
                ulid_id = comment_file.stem
                index.setdefault(target_id, []).append(ulid_id)

        for target_id, ulid_list in index.items():
            index_file = TARGETS_DIR / f"{target_id}.index.json"
            with index_file.open("w") as f:
                json.dump(sorted(ulid_list), f)

        return {"status": "rebuilt", "targets": list(index.keys())}
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid comment data: {str(e)}")


class SnapshotData(TypedDict):
    indexes: Dict[str, List[str]]
    flags: Dict[str, Dict[str, Any]]

@app.post("/admin/snapshot")
async def snapshot() -> dict:
    """
    Create a snapshot of all comment indexes and flags, saving them to a snapshot file.
    
    Returns:
        dict: A status dictionary containing confirmation and the snapshot file path.
    """
    snapshot_data: SnapshotData = {
        "indexes": {},
        "flags": {}
    }

    try:
        for index_file in TARGETS_DIR.glob("*.index.json"):
            with index_file.open() as f:
                snapshot_data["indexes"][index_file.stem] = json.load(f)

        for flag_file in FLAGS_DIR.glob("*.flags.json"):
            with flag_file.open() as f:
                snapshot_data["flags"][flag_file.stem] = json.load(f)

        with SNAPSHOT_FILE.open("w") as f:
            json.dump(snapshot_data, f, indent=2, sort_keys=True)

        return {"status": "snapshot created", "file": str(SNAPSHOT_FILE)}
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid data while creating snapshot: {str(e)}")

@app.get("/")
async def root() -> dict:
    """
    Return information about the SLAG Commenting API including its version.
    """
    return {
        "name": "SLAG Commenting API",
        "docs": "https://slag.example.com/docs",
        "version": __version__,
        "description": "A simple commenting system with support for ActivityStreams",
        "endpoints": {
            "root": "/",
            "comments": "/comments/{target_id}",
            "comment": "/comment/{ulid_id}",
            "reply": "/comment/{ulid_id}/reply",
            "flags": "/comment/{ulid_id}/flags",
            "admin": {
                "rebuild-index": "/admin/rebuild-index",
                "snapshot": "/admin/snapshot"
            }
        }
    }
