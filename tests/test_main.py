"""
Tests for the SLAG Commenting System API
"""
import shutil
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_env(monkeypatch):
    """Set up test environment before each test and clean up after."""
    base_test_dir = Path("test_temp_data")
    
    test_data_dir = base_test_dir / "slag-data"
    test_comments_dir = test_data_dir / "comments"
    test_targets_dir = test_data_dir / "targets"
    test_flags_dir = test_data_dir / "flags"
    test_snapshot_file = test_data_dir / "snapshot.json"

    test_comments_dir.mkdir(parents=True, exist_ok=True)
    test_targets_dir.mkdir(parents=True, exist_ok=True)
    test_flags_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("main.DATA_DIR", test_data_dir)
    monkeypatch.setattr("main.COMMENTS_DIR", test_comments_dir)
    monkeypatch.setattr("main.TARGETS_DIR", test_targets_dir)
    monkeypatch.setattr("main.FLAGS_DIR", test_flags_dir)
    monkeypatch.setattr("main.SNAPSHOT_FILE", test_snapshot_file)
    
    yield
    
    if base_test_dir.exists():
        shutil.rmtree(base_test_dir)


from datetime import datetime, timezone # Added for timestamp check
import re # For regex matching of timestamp

def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "SLAG Commenting API" # Adjusted to actual name


def test_create_and_get_comment(client):
    """Test creating and retrieving a comment."""
    target_id = "test-target-1"
    comment_input_data = {
        "content": "This is a test comment.",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    # Create a new comment
    response = client.post(f"/comments/{target_id}", json=comment_input_data)
    assert response.status_code == 200 # FastAPI default for POST with response model

    created_comment = response.json()
    assert created_comment["content"] == comment_input_data["content"]
    assert created_comment["attributedTo"]["name"] == comment_input_data["attributedTo"]["name"]
    assert "id" in created_comment
    comment_id_url = created_comment["id"]
    assert comment_id_url.startswith("https://slag.example.com/comments/")

    # Check the published field
    assert "published" in created_comment
    published_timestamp = created_comment["published"]
    # Example: 2024-01-11T10:40:09.123456Z
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$", published_timestamp)
    # Further check: parse it back to a datetime object
    dt_obj = datetime.fromisoformat(published_timestamp.replace("Z", "+00:00"))
    assert dt_obj.tzinfo == timezone.utc

    # Retrieve the comment directly by its ULID
    ulid_id = comment_id_url.split("/")[-1]
    response = client.get(f"/comment/{ulid_id}")
    assert response.status_code == 200
    retrieved_comment = response.json()
    assert retrieved_comment["content"] == comment_input_data["content"]
    assert retrieved_comment["published"] == published_timestamp

    # Retrieve all comments for the target
    response = client.get(f"/comments/{target_id}")
    assert response.status_code == 200
    collection = response.json()
    assert collection["totalItems"] == 1
    assert len(collection["orderedItems"]) == 1
    assert collection["orderedItems"][0] == comment_id_url


def test_update_comment(client):
    """Test updating a comment."""
    # Create a new comment
    page_id = "test-page-2"
    comment_data = {
        "author": "Test User",
        "text": "This is a test comment."
    }
    
    response = client.post(f"/comments/{page_id}", json=comment_data)
    comment_uuid = response.json()["uuid"]
    
    # Update the comment
    update_data = {
        "text": "This is an updated comment."
    }
    
    response = client.put(f"/comments/{page_id}/{comment_uuid}", json=update_data)
    assert response.status_code == 200
    assert response.json()["text"] == "This is an updated comment."
    
    # Verify the update
    response = client.get(f"/comments/{page_id}")
    assert response.json()["comments"][0]["text"] == "This is an updated comment."


def test_delete_comment(client):
    """Test deleting a comment."""
    # Create a new comment
    page_id = "test-page-3"
    comment_data = {
        "author": "Test User",
        "text": "This comment will be deleted."
    }
    
    response = client.post(f"/comments/{page_id}", json=comment_data)
    comment_uuid = response.json()["uuid"]
    
    # Delete the comment
    response = client.delete(f"/comments/{page_id}/{comment_uuid}")
    assert response.status_code == 200
    assert "Comment deleted successfully" in response.json()["detail"]
    
    # Verify the comment is deleted
    response = client.get(f"/comments/{page_id}")
    assert len(response.json()["comments"]) == 0


def test_create_and_get_reply(client):
    """Test creating and retrieving a reply to a comment."""
    # Create a parent comment
    page_id = "test-page-4"
    comment_data = {
        "author": "Parent Author",
        "text": "This is a parent comment."
    }
    
    response = client.post(f"/comments/{page_id}", json=comment_data)
    parent_uuid = response.json()["uuid"]
    
    # Create a reply
    reply_data = {
        "author": "Reply Author",
        "text": "This is a reply to the parent comment."
    }
    
    response = client.post(f"/comments/{page_id}/replies/{parent_uuid}", json=reply_data)
    assert response.status_code == 201
    assert response.json()["parent"] == parent_uuid
    
    # Get the replies
    response = client.get(f"/comments/{page_id}/replies/{parent_uuid}")
    assert response.status_code == 200
    assert len(response.json()["replies"]) == 1
    assert response.json()["replies"][0]["text"] == "This is a reply to the parent comment."
