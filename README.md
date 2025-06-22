# SLAG Commenting

Commenting system based on storing json files in a directory structure - each comment thread is a separate json file, allowing for easy retrieval and management of comments.

We provide an API using FastAPI to interact with the comment threads. The API allows you to create, read, update, and delete comments on specific pages.

```json
// Example JSON structure for a comment thread
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://example.com/schemas/page_comments.schema.json",
  "title": "Page Comments Schema",
  "description": "Schema for managing comments on a specific page.",
  "type": "object",
  "required": [
    "page_id",
    "comments"
  ],
  "properties": {
    "page_id": {
      "type": "string",
      "format": "uuid",
      "description": "The unique identifier of the page to which these comments belong."
    },
    "comments": {
      "type": "array",
      "description": "A list of comments associated with the page.",
      "items": {
        "type": "object",
        "description": "A single comment object.",
        "required": [
          "uuid",
          "author",
          "datetime",
          "text"
        ],
        "properties": {
          "uuid": {
            "type": "string",
            "format": "uuid",
            "description": "The unique identifier of the comment."
          },
          "author": {
            "type": "string",
            "description": "The name or identifier of the comment author.",
            "minLength": 1
          },
          "datetime": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time the comment was posted, in ISO 8601 format (e.g., '2023-10-27T10:00:00Z')."
          },
          "text": {
            "type": "string",
            "description": "The actual text content of the comment.",
            "minLength": 1
          },
          "parent": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the parent comment if this is a reply; null if it is a top-level comment.",
            "default": null
          },
          "flags": {
            "type": "object",
            "description": "Status flags for the comment.",
            "properties": {
              "hidden": {
                "type": "boolean",
                "description": "True if the comment is hidden from public view.",
                "default": false
              },
              "moderated": {
                "type": "boolean",
                "description": "True if the comment has been reviewed and approved by a moderator.",
                "default": false
              },
              "reported": {
                "type": "boolean",
                "description": "True if the comment has been reported by a user.",
                "default": false
              },
              "deleted": {
                "type": "boolean",
                "description": "True if the comment has been soft-deleted (e.g., not visible but retained for history).",
                "default": false
              }
            },
            "additionalProperties": false,
            "default": {}
          }
        }
      }
    }
  },
  "examples": [
    {
      "page_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "comments": [
        {
          "uuid": "fedcba98-7654-3210-fedc-ba9876543210",
          "author": "Alice Wonderland",
          "datetime": "2023-10-26T14:30:00Z",
          "text": "This is a fantastic page! Very informative.",
          "flags": {
            "hidden": false,
            "moderated": true,
            "reported": false
          }
        },
        {
          "uuid": "00112233-4455-6677-8899-aabbccddeeff",
          "author": "Bob The Builder",
          "datetime": "2023-10-27T09:15:00Z",
          "text": "I found a typo on line 5. Otherwise, great content!",
          "flags": {
            "hidden": false,
            "moderated": false
          }
        },
        {
          "uuid": "abcdef12-3456-7890-abcd-ef1234567890",
          "author": "Spam User",
          "datetime": "2023-10-27T10:05:00Z",
          "text": "Buy my super product for 50% off! Link in bio.",
          "flags": {
            "hidden": true,
            "moderated": true,
            "reported": true,
            "deleted": false
          }
        }
      ]
    },
    {
      "page_id": "99887766-5544-3322-1100-ffeeddccbbaa",
      "comments": []
    }
  ]
}
```

# API Endpoints

- `GET /comments/{page_id}`: Retrieve all comments for a specific page.
- `POST /comments/{page_id}`: Create a new comment on a specific page.
- `PUT /comments/{page_id}/{comment_uuid}`: Update an existing comment.
- `DELETE /comments/{page_id}/{comment_uuid}`: Delete a comment by UUID.
- `GET /comments/{page_id}/replies/{parent_uuid}`: Retrieve all replies to a specific comment.
- `POST /comments/{page_id}/replies/{parent_uuid}`: Create a new reply to a specific comment.
- `PUT /comments/{page_id}/replies/{parent_uuid}/{reply_uuid}`: Update an existing reply.
- `DELETE /comments/{page_id}/replies/{parent_uuid}/{reply_uuid}`: Delete a reply by UUID.

# FastAPI Documentation

You can access the automatically generated API documentation at `/docs` or `/redoc` after running the FastAPI application. This documentation provides an interactive interface to test the API endpoints.

# Running the Application

To set up and run the FastAPI application, follow these steps:

1. Make sure you have Python 3.11+ installed.

2. Set up a virtual environment and install dependencies using uv:

```bash
# Create and activate the virtual environment
uv venv
. .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install dependencies (choose one of the following methods)
# Method 1: Install from pyproject.toml
uv pip install -e .

# Method 2: Install from requirements.txt
uv pip install -r requirements.txt
```

3. Run the FastAPI application:

```bash
# Start the server with auto-reload for development
uvicorn main:app --reload
# Or using uv run
uv run uvicorn main:app --reload
```

4. The server will start at http://127.0.0.1:8000, and you can access the API documentation at http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc.

# Testing

To run the tests:

```bash
pytest
```

For test coverage:

```bash
pytest --cov=.
```

