"""
Tests for the SLAG Commenting System API
"""
import shutil
from pathlib import Path
import re  # For regex matching of timestamp
from datetime import datetime, timezone  # Added for timestamp check
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_env(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
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


def test_read_root(client: TestClient) -> None:
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "SLAG Commenting API" # Adjusted to actual name


def test_create_and_get_comment(client: TestClient) -> None:
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


def test_update_comment(client: TestClient) -> None:
    """Test updating a comment."""
    # Create a new comment
    target_id = "test-page-2"
    comment_input_data = {
        "content": "This is a test comment.",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    # Create the initial comment
    response = client.post(f"/comments/{target_id}", json=comment_input_data)
    assert response.status_code == 200
    comment_id_url = response.json()["id"]
    ulid_id = comment_id_url.split("/")[-1]
    
    # Update the comment
    update_data = {
        "content": "This is an updated comment.",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    response = client.patch(f"/comment/{ulid_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["content"] == "This is an updated comment."
    
    # Verify the update
    response = client.get(f"/comment/{ulid_id}")
    assert response.status_code == 200
    assert response.json()["content"] == "This is an updated comment."


def test_flags_comment(client: TestClient) -> None:
    """Test setting and getting flags for a comment."""
    # Create a new comment
    target_id = "test-page-3"
    comment_input_data = {
        "content": "This comment will be flagged.",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    # Create the comment
    response = client.post(f"/comments/{target_id}", json=comment_input_data)
    assert response.status_code == 200
    comment_id_url = response.json()["id"]
    ulid_id = comment_id_url.split("/")[-1]
    
    # Check initial flags (should be empty)
    response = client.get(f"/comment/{ulid_id}/flags")
    assert response.status_code == 200
    assert response.json() == {}
      # Set flags on the comment
    flag_data = {
        "hidden": True,
        "reported": True
    }
    response = client.patch(f"/comment/{ulid_id}/flags", json=flag_data)
    assert response.status_code == 200
    assert response.json()["hidden"] is True
    assert response.json()["reported"] is True
    
    # Verify the flags
    response = client.get(f"/comment/{ulid_id}/flags")
    assert response.status_code == 200
    assert response.json()["hidden"] is True
    assert response.json()["reported"] is True
    
    # Update just one flag
    update_data = {
        "moderated": True
    }
    
    response = client.patch(f"/comment/{ulid_id}/flags", json=update_data)
    assert response.status_code == 200
    assert response.json()["hidden"] is True  # Unchanged
    assert response.json()["reported"] is True  # Unchanged
    assert response.json()["moderated"] is True  # Added


def test_create_and_get_reply(client: TestClient) -> None:
    """Test creating and retrieving a reply to a comment."""
    # Create a parent comment
    target_id = "test-page-4"
    comment_input_data = {
        "content": "This is a parent comment.",
        "attributedTo": {
            "id": "http://example.com/users/parentuser",
            "name": "Parent User",
            "type": "Person"
        }
    }
    
    # Create the parent comment
    response = client.post(f"/comments/{target_id}", json=comment_input_data)
    assert response.status_code == 200
    parent_comment = response.json()
    parent_id_url = parent_comment["id"]
    parent_ulid = parent_id_url.split("/")[-1]
    
    # Create a reply
    reply_input_data = {
        "content": "This is a reply to the parent comment.",
        "attributedTo": {
            "id": "http://example.com/users/replyuser",
            "name": "Reply User",
            "type": "Person"
        }
    }
    
    response = client.post(f"/comment/{parent_ulid}/reply", json=reply_input_data)
    assert response.status_code == 200
    reply = response.json()
    assert reply["inReplyTo"] == parent_id_url
    assert reply["content"] == "This is a reply to the parent comment."
    
    # Get the reply by its ID
    reply_ulid = reply["id"].split("/")[-1]
    response = client.get(f"/comment/{reply_ulid}")
    assert response.status_code == 200
    retrieved_reply = response.json()
    assert retrieved_reply["content"] == "This is a reply to the parent comment."
    assert retrieved_reply["inReplyTo"] == parent_id_url
    
    # Check that both comments appear in the target's comment collection
    response = client.get(f"/comments/{target_id}")
    assert response.status_code == 200
    collection = response.json()
    assert collection["totalItems"] == 2
    assert len(collection["orderedItems"]) == 2
    assert parent_id_url in collection["orderedItems"]
    assert reply["id"] in collection["orderedItems"]


def test_admin_rebuild_index(client: TestClient) -> None:
    """Test the admin rebuild-index endpoint."""
    # Create two comments for different targets
    target1_id = "test-target-rebuild-1"
    target2_id = "test-target-rebuild-2"
    
    comment_input_data = {
        "content": "Comment for target 1",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    # Create comment for target 1
    client.post(f"/comments/{target1_id}", json=comment_input_data)
    
    # Create comment for target 2
    comment_input_data["content"] = "Comment for target 2"
    client.post(f"/comments/{target2_id}", json=comment_input_data)
    
    # Rebuild the index
    response = client.post("/admin/rebuild-index")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "rebuilt"
    assert target1_id in result["targets"]
    assert target2_id in result["targets"]
    
def test_admin_snapshot(client: TestClient) -> None:
    """Test the admin snapshot endpoint."""
    # Create a comment and set flags
    target_id = "test-target-snapshot"
    comment_input_data = {
        "content": "Comment for snapshot test",
        "attributedTo": {
            "id": "http://example.com/users/testuser",
            "name": "Test User",
            "type": "Person"
        }
    }
    
    # Create the comment
    response = client.post(f"/comments/{target_id}", json=comment_input_data)
    comment_id_url = response.json()["id"]
    ulid_id = comment_id_url.split("/")[-1]
    
    # Set flags for the comment
    flag_data = {
        "hidden": True,
        "reported": True
    }
    client.patch(f"/comment/{ulid_id}/flags", json=flag_data)
    
    # Create snapshot
    response = client.post("/admin/snapshot")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "snapshot created"
    assert "file" in result
    assert str(result["file"]).endswith("snapshot.json")
