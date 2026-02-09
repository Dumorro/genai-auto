# GenAI Auto -- API Reference

Complete API reference for the GenAI Auto multi-agent AI system for automotive customer service.

**Version:** 1.0.0
**Base framework:** FastAPI

---

## Table of Contents

- [Base URL](#base-url)
- [Interactive Documentation](#interactive-documentation)
- [Authentication Flow](#authentication-flow)
- [Error Response Format](#error-response-format)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Authentication](#authentication)
  - [Chat](#chat)
  - [WebSocket](#websocket)
  - [Documents](#documents)
  - [Metrics and Feedback](#metrics-and-feedback)
  - [Evaluation](#evaluation)
  - [Frontend](#frontend)

---

## Base URL

```
http://localhost:8000
```

All REST API endpoints (except health, WebSocket, and frontend) are prefixed with `/api/v1`.

| Environment | Base URL                          |
|-------------|-----------------------------------|
| Local dev   | `http://localhost:8000`            |
| Docker      | `http://localhost:8000`            |
| Production  | `https://your-domain.com`         |

---

## Interactive Documentation

GenAI Auto ships with two auto-generated interactive API documentation UIs, courtesy of FastAPI:

| UI      | URL          | Description                                    |
|---------|--------------|------------------------------------------------|
| Swagger | `/docs`      | Interactive Swagger UI -- try endpoints live    |
| ReDoc   | `/redoc`     | Read-only API documentation with search         |

Both pages are generated automatically from the route definitions and Pydantic models and require no authentication to access.

---

## Authentication Flow

GenAI Auto uses **JWT (JSON Web Token)** authentication with access and refresh tokens.

### How it works

1. **Register** or **Login** to receive an `access_token` and a `refresh_token`.
2. Include the `access_token` in the `Authorization` header for protected endpoints.
3. When the access token expires (default: 30 minutes), use the `refresh_token` to obtain a new pair.
4. Refresh tokens expire after 7 days by default.

### Token format

```
Authorization: Bearer <access_token>
```

### Token lifecycle

```
Register/Login --> access_token (30 min) + refresh_token (7 days)
                        |                           |
                  Use for API calls          Use to get new tokens
                        |                           |
                  Token expires              POST /api/v1/auth/refresh
                        |                           |
                  401 Unauthorized           New access_token + refresh_token
```

### Auth requirements by endpoint

| Requirement    | Meaning                                                           |
|----------------|-------------------------------------------------------------------|
| **Required**   | Must include a valid `Authorization: Bearer <token>` header       |
| **Optional**   | Works without auth; auth adds user context if provided            |
| **None**       | No authentication needed                                         |

---

## Error Response Format

All API errors follow a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP status codes

| Code | Meaning               | When it occurs                                          |
|------|-----------------------|---------------------------------------------------------|
| 400  | Bad Request           | Invalid input, validation error, duplicate email        |
| 401  | Unauthorized          | Missing or invalid token, expired token                 |
| 404  | Not Found             | Resource does not exist                                 |
| 422  | Unprocessable Entity  | Request body fails Pydantic validation                  |
| 500  | Internal Server Error | Unexpected server-side failure                          |

### Validation error format (422)

When Pydantic validation fails, FastAPI returns a structured error:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Endpoints

---

### Health

Health check endpoints have no `/api/v1` prefix. They are mounted at the application root.

---

#### GET /health

Basic liveness check. Returns immediately, no dependencies checked.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |
| Rate limited  | No          |

**Response (200)**

```json
{
  "status": "healthy"
}
```

**curl**

```bash
curl http://localhost:8000/health
```

---

#### GET /health/ready

Readiness check that verifies database connectivity.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |
| Rate limited  | No          |

**Response (200) -- ready**

```json
{
  "status": "ready",
  "database": "connected"
}
```

**Response (200) -- not ready**

```json
{
  "status": "not_ready",
  "database": "error: connection refused"
}
```

**curl**

```bash
curl http://localhost:8000/health/ready
```

---

### Authentication

All auth endpoints are prefixed with `/api/v1/auth`.

---

#### POST /api/v1/auth/register

Create a new user account and receive JWT tokens.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Request body**

| Field      | Type   | Required | Constraints          | Description             |
|------------|--------|----------|----------------------|-------------------------|
| `email`    | string | Yes      | Valid email address  | User email              |
| `password` | string | Yes      | min length: 8        | Account password        |
| `name`     | string | Yes      | min length: 2        | Display name            |

```json
{
  "email": "john@example.com",
  "password": "securepass123",
  "name": "John Doe"
}
```

**Response (200)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

**Error responses**

| Code | Detail                      | Cause                         |
|------|-----------------------------|-------------------------------|
| 400  | `Email already registered`  | Duplicate email address       |
| 422  | Validation error            | Invalid email, short password |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepass123",
    "name": "John Doe"
  }'
```

---

#### POST /api/v1/auth/login

Authenticate with existing credentials and receive JWT tokens.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Request body**

| Field      | Type   | Required | Description        |
|------------|--------|----------|--------------------|
| `email`    | string | Yes      | Registered email   |
| `password` | string | Yes      | Account password   |

```json
{
  "email": "john@example.com",
  "password": "securepass123"
}
```

**Response (200)**

Same schema as the register endpoint:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

**Error responses**

| Code | Detail                       | Cause                          |
|------|------------------------------|--------------------------------|
| 401  | `Invalid email or password`  | Wrong credentials              |
| 422  | Validation error             | Missing or malformed fields    |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

---

#### POST /api/v1/auth/refresh

Exchange a valid refresh token for a new access/refresh token pair.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Request body**

| Field           | Type   | Required | Description                |
|-----------------|--------|----------|----------------------------|
| `refresh_token` | string | Yes      | A valid refresh token      |

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

**Error responses**

| Code | Detail                    | Cause                                    |
|------|---------------------------|------------------------------------------|
| 401  | `Invalid token`           | Malformed or expired refresh token       |
| 401  | `Invalid refresh token`   | An access token was passed instead       |
| 401  | `User not found`          | The user account no longer exists        |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

#### GET /api/v1/auth/me

Return the profile of the currently authenticated user.

| Property      | Value       |
|---------------|-------------|
| Auth required | **Required** |

**Request headers**

```
Authorization: Bearer <access_token>
```

**Response (200)**

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "name": "John Doe"
}
```

**Error responses**

| Code | Detail                       | Cause                           |
|------|------------------------------|---------------------------------|
| 401  | `Authentication required`    | No token provided               |
| 401  | `Invalid token`              | Token is malformed or expired   |
| 401  | `Invalid access token`       | A refresh token was used        |

**curl**

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Chat

The chat endpoint processes messages through the multi-agent AI system (LangGraph workflow). The system classifies the intent and routes to the appropriate specialized agent (specs, scheduling, general, etc.).

---

#### POST /api/v1/chat

Send a message and receive an AI-generated response.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Request body**

| Field         | Type   | Required | Default | Description                            |
|---------------|--------|----------|---------|----------------------------------------|
| `message`     | string | Yes      | --      | The user's message                     |
| `session_id`  | string | No       | auto    | Session ID for conversation continuity |
| `customer_id` | string (UUID) | No | null    | Customer ID if known                   |
| `vehicle_id`  | string (UUID) | No | null    | Vehicle ID if relevant                 |
| `metadata`    | object | No       | `{}`    | Additional context metadata            |

```json
{
  "message": "What are the specs for the 2024 Model X?",
  "session_id": "abc-123",
  "customer_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200)**

```json
{
  "response": "The 2024 Model X features a 3.5L V6 engine with 300 horsepower...",
  "session_id": "abc-123",
  "agent_used": "specs",
  "metadata": {
    "confidence": 0.95,
    "sources": ["specs_manual_2024.pdf"]
  }
}
```

**Response fields**

| Field        | Type   | Description                                       |
|--------------|--------|---------------------------------------------------|
| `response`   | string | The AI-generated answer                           |
| `session_id` | string | Session ID (auto-generated if not provided)       |
| `agent_used` | string | Which agent handled the request (e.g., `specs`, `scheduling`, `orchestrator`) |
| `metadata`   | object | Context from the agent pipeline                   |

**Error responses**

| Code | Detail                              | Cause                                |
|------|-------------------------------------|--------------------------------------|
| 422  | Validation error                    | Missing `message` field              |
| 500  | `Failed to process message: <err>`  | LLM or workflow failure              |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the specs for the 2024 Model X?",
    "session_id": "abc-123"
  }'
```

---

#### GET /api/v1/chat/history/{session_id}

Retrieve chat history for a given session.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

> **Note:** This endpoint is currently a placeholder (returns empty messages). Full implementation is planned.

**Path parameters**

| Parameter    | Type   | Description            |
|--------------|--------|------------------------|
| `session_id` | string | The session to look up |

**Response (200)**

```json
{
  "session_id": "abc-123",
  "messages": []
}
```

**curl**

```bash
curl http://localhost:8000/api/v1/chat/history/abc-123
```

---

### WebSocket

Real-time streaming chat over WebSocket. See [docs/WEBSOCKET.md](WEBSOCKET.md) for the full protocol specification.

---

#### WS /ws/chat

Streaming chat endpoint. Connects over WebSocket for real-time, token-by-token response streaming with progress updates.

| Property      | Value                                 |
|---------------|---------------------------------------|
| Auth required | None (PoC mode)                       |
| Protocol      | WebSocket (ws:// or wss://)           |

**Connection URL**

```
ws://localhost:8000/ws/chat
```

**Client-to-server message (send a chat message)**

```json
{
  "type": "message",
  "message": "What maintenance does a 2024 Model X need?",
  "session_id": "optional-session-id",
  "customer_id": "optional-customer-id"
}
```

**Server-to-client: progress update**

```json
{
  "type": "progress",
  "step": "rag_retrieval",
  "message": "Searching knowledge base..."
}
```

Progress steps are sent in order: `starting` -> `agent_routing` -> `rag_retrieval` -> response.

**Server-to-client: streaming token**

```json
{
  "type": "token",
  "token": "The ",
  "partial_response": "The "
}
```

**Server-to-client: complete response**

```json
{
  "type": "complete",
  "response": "The 2024 Model X requires oil changes every 5,000 miles...",
  "session_id": "session-ws_1234567890",
  "metadata": {
    "agent": "specs",
    "confidence": 0.95,
    "context": {}
  }
}
```

**Server-to-client: error**

```json
{
  "type": "error",
  "error": "Message is required",
  "code": "EMPTY_MESSAGE"
}
```

**Error codes**

| Code               | Meaning                                       |
|--------------------|-----------------------------------------------|
| `EMPTY_MESSAGE`    | The `message` field was empty or missing       |
| `PROCESSING_ERROR` | An error occurred during agent processing      |

**JavaScript connection example**

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "message",
    message: "What are the specs for the 2024 Model X?",
    session_id: "my-session-1"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case "progress":
      console.log("Progress:", data.message);
      break;
    case "token":
      process.stdout.write(data.token);
      break;
    case "complete":
      console.log("\nFull response:", data.response);
      break;
    case "error":
      console.error("Error:", data.error);
      break;
  }
};
```

---

#### GET /ws/test

An HTML test page for interactively testing the WebSocket chat endpoint in a browser.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |
| Response      | HTML page   |

**curl**

```bash
curl http://localhost:8000/ws/test
```

Open in a browser: `http://localhost:8000/ws/test`

---

### Documents

Document management endpoints for the RAG (Retrieval-Augmented Generation) knowledge base. All endpoints are prefixed with `/api/v1/documents`.

---

#### POST /api/v1/documents/upload

Upload a file and ingest it into the vector knowledge base. The file is chunked, embedded, and stored for semantic search.

| Property      | Value           |
|---------------|-----------------|
| Auth required | **Required**    |
| Content-Type  | multipart/form-data |

**Supported file formats:** PDF (.pdf), Word (.docx), Text (.txt), Markdown (.md)

**Form fields**

| Field           | Type    | Required | Default  | Description                   |
|-----------------|---------|----------|----------|-------------------------------|
| `file`          | file    | Yes      | --       | The document file to upload   |
| `document_type` | string  | No       | `manual` | Document category             |
| `chunk_size`    | integer | No       | `1000`   | Characters per chunk          |
| `chunk_overlap` | integer | No       | `200`    | Overlap between chunks        |

**Response (200)**

```json
{
  "document_id": "d4f7a8b2-1234-5678-9abc-def012345678",
  "filename": "specs_manual_2024.pdf",
  "document_type": "manual",
  "chunks_created": 42,
  "tokens_used": 15230,
  "chunking_strategy": "recursive"
}
```

**Error responses**

| Code | Detail                                    | Cause                         |
|------|-------------------------------------------|-------------------------------|
| 400  | `Empty file`                              | Uploaded file has 0 bytes     |
| 400  | `File too large (max 50MB)`               | File exceeds 50 MB limit     |
| 400  | Validation error                          | Unsupported format, etc.      |
| 401  | `Authentication required`                 | Missing or invalid token      |
| 500  | `Failed to process document: <err>`       | Processing pipeline failure   |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@specs_manual_2024.pdf" \
  -F "document_type=manual" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200"
```

---

#### POST /api/v1/documents/ingest-text

Ingest raw text directly into the knowledge base (no file upload needed).

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Request body**

| Field               | Type   | Required | Default  | Description                       |
|---------------------|--------|----------|----------|-----------------------------------|
| `text`              | string | Yes      | --       | Text content to ingest            |
| `source`            | string | Yes      | --       | Source identifier (e.g., URL)     |
| `document_type`     | string | No       | `manual` | Document category                 |
| `chunking_strategy` | string | No       | null     | Chunking strategy override        |
| `metadata`          | object | No       | `{}`     | Additional metadata               |

```json
{
  "text": "The 2024 Model X features a turbocharged 2.0L engine...",
  "source": "product_catalog_2024",
  "document_type": "specs",
  "metadata": {
    "year": 2024,
    "model": "Model X"
  }
}
```

**Response (200)**

```json
{
  "document_id": "a1b2c3d4-5678-9abc-def0-123456789abc",
  "filename": "product_catalog_2024",
  "document_type": "specs",
  "chunks_created": 5,
  "tokens_used": 1024,
  "chunking_strategy": "recursive"
}
```

**Error responses**

| Code | Detail                       | Cause                         |
|------|------------------------------|-------------------------------|
| 400  | Validation error             | Missing required fields       |
| 401  | `Authentication required`    | Missing or invalid token      |
| 500  | Processing error             | Chunking or embedding failure |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest-text \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The 2024 Model X features a turbocharged 2.0L engine...",
    "source": "product_catalog_2024",
    "document_type": "specs"
  }'
```

---

#### POST /api/v1/documents/search

Perform a semantic similarity search across the knowledge base.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Optional** |

**Request body**

| Field           | Type   | Required | Default | Constraints   | Description                        |
|-----------------|--------|----------|---------|---------------|------------------------------------|
| `query`         | string | Yes      | --      | --            | Natural language search query      |
| `top_k`         | integer| No       | `5`     | 1--20         | Number of results to return        |
| `document_type` | string | No       | null    | --            | Filter results by document type    |
| `source`        | string | No       | null    | --            | Filter results by source           |
| `min_score`     | float  | No       | `0.5`   | 0.0--1.0      | Minimum similarity score threshold |

```json
{
  "query": "engine specifications 2024",
  "top_k": 3,
  "document_type": "specs",
  "min_score": 0.7
}
```

**Response (200)**

```json
{
  "results": [
    {
      "content": "The 2024 Model X features a 3.5L V6 engine producing 300 HP...",
      "score": 0.92,
      "metadata": {
        "document_type": "specs",
        "chunk_index": 3
      },
      "source": "specs_manual_2024.pdf"
    },
    {
      "content": "Engine maintenance intervals for the 2024 lineup...",
      "score": 0.85,
      "metadata": {
        "document_type": "manual",
        "chunk_index": 12
      },
      "source": "maintenance_guide.pdf"
    }
  ],
  "query": "engine specifications 2024",
  "total": 2
}
```

**Error responses**

| Code | Detail             | Cause                          |
|------|--------------------|--------------------------------|
| 422  | Validation error   | Missing query, top_k out of range |
| 500  | Search error       | Vector store or embedding failure  |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "engine specifications 2024",
    "top_k": 3,
    "min_score": 0.7
  }'
```

With authentication (optional):

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "engine specifications 2024"
  }'
```

---

#### GET /api/v1/documents/

List all documents currently stored in the knowledge base.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Response (200)**

```json
{
  "documents": [
    {
      "source": "specs_manual_2024.pdf",
      "document_type": "manual",
      "chunk_count": 42,
      "first_indexed": "2025-01-15T10:30:00Z",
      "last_indexed": "2025-01-15T10:30:00Z"
    },
    {
      "source": "product_catalog_2024",
      "document_type": "specs",
      "chunk_count": 5,
      "first_indexed": "2025-01-16T08:00:00Z",
      "last_indexed": "2025-01-16T08:00:00Z"
    }
  ]
}
```

**Error responses**

| Code | Detail                    | Cause                    |
|------|---------------------------|--------------------------|
| 401  | `Authentication required` | Missing or invalid token |

**curl**

```bash
curl http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/v1/documents/stats

Return aggregate statistics for the knowledge base.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Optional** |

**Response (200)**

```json
{
  "total_chunks": 128,
  "total_sources": 5,
  "total_document_types": 3
}
```

**curl**

```bash
curl http://localhost:8000/api/v1/documents/stats
```

---

#### DELETE /api/v1/documents/{source}

Delete a document and all its chunks from the knowledge base.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Path parameters**

| Parameter | Type   | Description                                        |
|-----------|--------|----------------------------------------------------|
| `source`  | string | Source identifier of the document (supports `/` in path) |

**Response (200)**

```json
{
  "message": "Document deleted",
  "source": "specs_manual_2024.pdf",
  "chunks_deleted": 42
}
```

**Error responses**

| Code | Detail                    | Cause                              |
|------|---------------------------|------------------------------------|
| 401  | `Authentication required` | Missing or invalid token           |
| 404  | `Document not found`      | No document with the given source  |

**curl**

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/specs_manual_2024.pdf \
  -H "Authorization: Bearer <access_token>"
```

---

### Metrics and Feedback

Observability and user feedback endpoints. All endpoints are prefixed with `/api/v1`.

---

#### GET /api/v1/metrics

Prometheus metrics endpoint for scraping. Returns metrics in Prometheus text exposition format.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |
| Response      | Prometheus text format |

**Response (200)**

```
# HELP genai_auto_requests_total Total requests
# TYPE genai_auto_requests_total counter
genai_auto_requests_total{method="POST",endpoint="/api/v1/chat"} 142
# HELP genai_auto_response_latency_seconds Response latency
# TYPE genai_auto_response_latency_seconds histogram
genai_auto_response_latency_seconds_bucket{le="0.5"} 89
...
```

**curl**

```bash
curl http://localhost:8000/api/v1/metrics
```

---

#### POST /api/v1/feedback

Submit user feedback (thumbs up/down) for a specific message. Tracked in Prometheus counters.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Request body**

| Field        | Type   | Required | Description                                |
|--------------|--------|----------|--------------------------------------------|
| `message_id` | string | Yes      | ID of the message being rated              |
| `sentiment`  | string | Yes      | `"positive"` or `"negative"`               |
| `comment`    | string | No       | Optional free-text comment                 |

```json
{
  "message_id": "msg_abc123",
  "sentiment": "positive",
  "comment": "Very helpful answer!"
}
```

**Response (200)**

```json
{
  "status": "success",
  "message": "Feedback recorded",
  "message_id": "msg_abc123",
  "sentiment": "positive"
}
```

**Error responses**

| Code | Detail           | Cause                                                |
|------|------------------|------------------------------------------------------|
| 422  | Validation error | Missing fields or sentiment not `positive`/`negative`|

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_abc123",
    "sentiment": "positive",
    "comment": "Very helpful answer!"
  }'
```

---

#### GET /api/v1/metrics/summary

Human-readable metrics summary for dashboards and admin UIs.

| Property      | Value       |
|---------------|-------------|
| Auth required | None        |

**Response (200)**

```json
{
  "status": "ok",
  "message": "Use /metrics endpoint for Prometheus scraping, or set up Grafana dashboard",
  "endpoints": {
    "prometheus": "/api/v1/metrics",
    "feedback": "/api/v1/feedback"
  }
}
```

**curl**

```bash
curl http://localhost:8000/api/v1/metrics/summary
```

---

### Evaluation

RAG quality evaluation endpoints for measuring retrieval and generation performance. All endpoints are prefixed with `/api/v1/evaluation`. All evaluation endpoints require authentication.

---

#### POST /api/v1/evaluation/single

Evaluate a single query and return detailed quality metrics.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Request body**

| Field             | Type   | Required | Default | Constraints | Description                      |
|-------------------|--------|----------|---------|-------------|----------------------------------|
| `query`           | string | Yes      | --      | --          | Query to evaluate                |
| `expected_answer` | string | No       | null    | --          | Expected answer for comparison   |
| `k`               | integer| No       | `5`     | 1--20       | Number of documents to retrieve  |

```json
{
  "query": "What engine does the 2024 Model X have?",
  "expected_answer": "3.5L V6 with 300 horsepower",
  "k": 5
}
```

**Response (200)**

```json
{
  "query": "What engine does the 2024 Model X have?",
  "generated_answer": "The 2024 Model X features a 3.5L V6 engine producing 300 HP...",
  "retrieval_metrics": {
    "precision": 0.8,
    "recall": 0.9,
    "mrr": 0.85
  },
  "generation_metrics": {
    "faithfulness": 0.95,
    "relevance": 0.92,
    "correctness": 0.88
  },
  "latency_metrics": {
    "retrieval_ms": 120,
    "generation_ms": 850,
    "total_ms": 970
  },
  "overall_score": 0.89
}
```

**Error responses**

| Code | Detail                    | Cause                    |
|------|---------------------------|--------------------------|
| 401  | `Authentication required` | Missing or invalid token |
| 500  | Evaluation error          | Pipeline failure         |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/single \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What engine does the 2024 Model X have?",
    "expected_answer": "3.5L V6 with 300 horsepower"
  }'
```

---

#### POST /api/v1/evaluation/batch

Start a batch evaluation using the built-in sample dataset. Runs asynchronously in the background.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Request body**

| Field                | Type     | Required | Default | Description                          |
|----------------------|----------|----------|---------|--------------------------------------|
| `name`               | string   | Yes      | --      | Unique name for this evaluation run  |
| `use_sample_dataset` | boolean  | No       | `true`  | Use the built-in sample dataset      |
| `categories`         | string[] | No       | null    | Filter test cases by category        |
| `difficulties`       | string[] | No       | null    | Filter test cases by difficulty      |
| `k`                  | integer  | No       | `5`     | Number of documents to retrieve      |
| `max_concurrent`     | integer  | No       | `3`     | Max concurrent evaluations (1--10)   |

```json
{
  "name": "weekly-eval-2025-01",
  "use_sample_dataset": true,
  "categories": ["specs", "maintenance"],
  "k": 5,
  "max_concurrent": 3
}
```

**Response (200)**

```json
{
  "message": "Evaluation 'weekly-eval-2025-01' started",
  "status_endpoint": "/api/v1/evaluation/status/weekly-eval-2025-01"
}
```

**Error responses**

| Code | Detail                                       | Cause                           |
|------|----------------------------------------------|---------------------------------|
| 400  | `Evaluation '<name>' is already running`     | Duplicate evaluation name       |
| 400  | `Custom dataset not provided...`             | `use_sample_dataset` is false   |
| 401  | `Authentication required`                    | Missing or invalid token        |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/batch \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weekly-eval-2025-01",
    "use_sample_dataset": true
  }'
```

---

#### POST /api/v1/evaluation/custom

Run an evaluation with user-provided test cases. Runs asynchronously in the background.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Request body**

| Field        | Type       | Required | Default | Description                          |
|--------------|------------|----------|---------|--------------------------------------|
| `name`       | string     | Yes      | --      | Unique name for this evaluation run  |
| `test_cases` | TestCase[] | Yes      | --      | Array of test cases (see below)      |
| `k`          | integer    | No       | `5`     | Number of documents to retrieve      |

**TestCase object**

| Field             | Type   | Required | Default    | Description              |
|-------------------|--------|----------|------------|--------------------------|
| `id`              | string | Yes      | --         | Unique test case ID      |
| `query`           | string | Yes      | --         | The query to evaluate    |
| `expected_answer` | string | No       | null       | Expected correct answer  |
| `category`        | string | No       | `general`  | Test case category       |
| `difficulty`      | string | No       | `medium`   | Difficulty level         |

```json
{
  "name": "custom-eval-01",
  "test_cases": [
    {
      "id": "tc-1",
      "query": "What is the towing capacity of the 2024 Model X?",
      "expected_answer": "7,500 lbs",
      "category": "specs",
      "difficulty": "easy"
    },
    {
      "id": "tc-2",
      "query": "How often should I rotate tires?",
      "category": "maintenance",
      "difficulty": "medium"
    }
  ],
  "k": 5
}
```

**Response (200)**

```json
{
  "message": "Custom evaluation 'custom-eval-01' started",
  "test_cases": 2
}
```

**Error responses**

| Code | Detail                                       | Cause                       |
|------|----------------------------------------------|-----------------------------|
| 400  | `Evaluation '<name>' is already running`     | Duplicate evaluation name   |
| 401  | `Authentication required`                    | Missing or invalid token    |

**curl**

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/custom \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom-eval-01",
    "test_cases": [
      {
        "id": "tc-1",
        "query": "What is the towing capacity of the 2024 Model X?",
        "expected_answer": "7,500 lbs",
        "category": "specs"
      }
    ]
  }'
```

---

#### GET /api/v1/evaluation/status/{name}

Check the status of a running or completed evaluation.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Path parameters**

| Parameter | Type   | Description              |
|-----------|--------|--------------------------|
| `name`    | string | Evaluation run name      |

**Response (200)**

```json
{
  "name": "weekly-eval-2025-01",
  "status": "running",
  "progress": 8,
  "total": 20,
  "message": ""
}
```

**Status values:** `pending`, `running`, `completed`, `failed`

**Error responses**

| Code | Detail                                | Cause                      |
|------|---------------------------------------|----------------------------|
| 401  | `Authentication required`             | Missing or invalid token   |
| 404  | `Evaluation '<name>' not found`       | No evaluation with that name |

**curl**

```bash
curl http://localhost:8000/api/v1/evaluation/status/weekly-eval-2025-01 \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/v1/evaluation/results/{name}

Retrieve the full results of a completed evaluation.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Path parameters**

| Parameter | Type   | Description              |
|-----------|--------|--------------------------|
| `name`    | string | Evaluation run name      |

**Response (200)**

Returns the full evaluation report as a JSON object (structure depends on the `EvaluationReport.to_dict()` output).

**Error responses**

| Code | Detail                                              | Cause                           |
|------|-----------------------------------------------------|---------------------------------|
| 400  | `Evaluation '<name>' is <status>. Results not available yet.` | Evaluation not yet completed |
| 401  | `Authentication required`                           | Missing or invalid token        |
| 404  | `Evaluation '<name>' not found`                     | No evaluation with that name    |

**curl**

```bash
curl http://localhost:8000/api/v1/evaluation/results/weekly-eval-2025-01 \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/v1/evaluation/results/{name}/summary

Get a text summary of evaluation results.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Response (200)**

```json
{
  "summary": "Evaluation 'weekly-eval-2025-01': 20 test cases, avg score 0.87..."
}
```

**Error responses**

| Code | Detail                           | Cause                      |
|------|----------------------------------|----------------------------|
| 401  | `Authentication required`        | Missing or invalid token   |
| 404  | `Evaluation '<name>' not found`  | No evaluation with that name |

**curl**

```bash
curl http://localhost:8000/api/v1/evaluation/results/weekly-eval-2025-01/summary \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/v1/evaluation/list

List all evaluation runs (running and completed).

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Response (200)**

```json
{
  "evaluations": [
    {
      "name": "weekly-eval-2025-01",
      "status": "completed",
      "has_results": true
    },
    {
      "name": "custom-eval-01",
      "status": "running",
      "has_results": false
    }
  ]
}
```

**curl**

```bash
curl http://localhost:8000/api/v1/evaluation/list \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/v1/evaluation/sample-dataset

Retrieve the built-in sample evaluation dataset.

| Property      | Value        |
|---------------|--------------|
| Auth required | **Required** |

**Response (200)**

```json
{
  "name": "genai-auto-sample",
  "total_cases": 20,
  "categories": ["specs", "maintenance", "scheduling", "general"],
  "difficulties": ["easy", "medium", "hard"],
  "test_cases": [
    {
      "id": "tc-001",
      "query": "What engine does the 2024 Model X have?",
      "expected_answer": "3.5L V6 with 300 HP",
      "category": "specs",
      "difficulty": "easy"
    }
  ]
}
```

**curl**

```bash
curl http://localhost:8000/api/v1/evaluation/sample-dataset \
  -H "Authorization: Bearer <access_token>"
```

---

### Frontend

Static frontend routes served when the `frontend/` directory exists at the project root.

---

#### GET /

Redirects to `/chat`.

| Property      | Value             |
|---------------|-------------------|
| Auth required | None              |
| Response      | 307 Redirect      |

---

#### GET /chat

Serves the main chat HTML page (`frontend/chat.html`).

| Property      | Value             |
|---------------|-------------------|
| Auth required | None              |
| Response      | HTML page         |

---

#### GET /static/*

Serves static files from the `frontend/` directory.

| Property      | Value             |
|---------------|-------------------|
| Auth required | None              |

Example: `http://localhost:8000/static/styles.css`

---

## Quick Start Example

A full end-to-end flow using curl:

```bash
# 1. Register a new user
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "demopass123",
    "name": "Demo User"
  }' | jq .

# 2. Save the access token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "demopass123"
  }' | jq -r .access_token)

# 3. Upload a document to the knowledge base
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@vehicle_manual.pdf" \
  -F "document_type=manual"

# 4. Ask a question via the chat API
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the recommended tire pressure for the 2024 Model X?"
  }' | jq .

# 5. Search the knowledge base directly
curl -s -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tire pressure",
    "top_k": 3
  }' | jq .

# 6. Submit feedback
curl -s -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_001",
    "sentiment": "positive",
    "comment": "Accurate answer!"
  }' | jq .

# 7. Check system health
curl -s http://localhost:8000/health | jq .
```
