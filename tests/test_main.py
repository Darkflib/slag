"""
Tests for the SLAG Commenting System API
"""
import shutil
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app, COMMENTS_DIR


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Set up test environment before each test and clean up after."""
    # Create temporary comments directory for tests
    test_comments_dir = Path("test_comments")
    test_comments_dir.mkdir(exist_ok=True)
    
    # Backup original comments directory path
    original_comments_dir = COMMENTS_DIR
    
    # Override the comments directory for testing
    global COMMENTS_DIR
    COMMENTS_DIR = test_comments_dir
    
    yield
    
    # Clean up test directory after tests
    if test_comments_dir.exists():
        shutil.rmtree(test_comments_dir)
    
    # Restore original comments directory
    COMMENTS_DIR = original_comments_dir


def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "SLAG Commenting System" in response.json()["name"]


def test_create_and_get_comment(client):
    """Test creating and retrieving a comment."""
    # Create a new comment
    page_id = "test-page-1"
    comment_data = {
        "author": "Test User",
        "text": "This is a test comment."
    }
    
    response = client.post(f"/comments/{page_id}", json=comment_data)
    assert response.status_code == 201
    
    # Get the comment UUID
    comment_uuid = response.json()["uuid"]
    
    # Verify the UUID is valid
    UUID(comment_uuid)
    
    # Retrieve all comments for the page
    response = client.get(f"/comments/{page_id}")
    assert response.status_code == 200
    assert len(response.json()["comments"]) == 1
    assert response.json()["comments"][0]["text"] == "This is a test comment."


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
