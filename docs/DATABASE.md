# Database Schema

## Overview

GenAI Auto uses **PostgreSQL 16** with the **pgvector** extension for vector similarity search. The database stores customer data, vehicle information, service records, RAG document embeddings, and conversation history.

- **ORM**: SQLAlchemy 2.0+ (async)
- **Driver**: asyncpg (async) / psycopg2-binary (sync)
- **Migrations**: Alembic
- **Vector Extension**: pgvector (cosine similarity)

---

## Entity-Relationship Diagram

```mermaid
erDiagram
    USER {
        uuid id PK
        string email UK
        string name
        string password_hash
        boolean is_active
        boolean is_admin
        timestamp created_at
        timestamp updated_at
    }

    CUSTOMER ||--o{ VEHICLE : owns
    CUSTOMER ||--o{ APPOINTMENT : schedules
    CUSTOMER ||--o{ CONVERSATION : has
    CUSTOMER {
        uuid id PK
        string name
        string email UK
        string phone
        timestamp created_at
        timestamp updated_at
    }

    VEHICLE ||--o{ SERVICE_HISTORY : has
    VEHICLE ||--o{ APPOINTMENT : for
    VEHICLE {
        uuid id PK
        uuid customer_id FK
        string brand
        string model
        int year
        string vin UK
        string license_plate
        timestamp created_at
        timestamp updated_at
    }

    SERVICE_HISTORY {
        uuid id PK
        uuid vehicle_id FK
        string service_type
        text description
        timestamp service_date
        int mileage
        decimal cost
        string status
        timestamp created_at
    }

    APPOINTMENT {
        uuid id PK
        uuid customer_id FK
        uuid vehicle_id FK
        string service_type
        timestamp scheduled_date
        text notes
        string status
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_EMBEDDING {
        uuid id PK
        text content
        jsonb doc_metadata
        vector embedding
        string source
        string document_type
        timestamp created_at
    }

    CONVERSATION {
        uuid id PK
        string session_id
        uuid customer_id FK
        jsonb messages
        jsonb conversation_metadata
        timestamp created_at
        timestamp updated_at
    }
```

---

## Tables

### users

Authentication and authorization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | User email |
| name | VARCHAR(255) | NOT NULL | Display name |
| password_hash | VARCHAR(255) | NOT NULL | Argon2 hashed password |
| is_active | BOOLEAN | default true | Account active status |
| is_admin | BOOLEAN | default false | Admin privileges |
| created_at | TIMESTAMP | default now() | Creation timestamp |
| updated_at | TIMESTAMP | default now(), on update | Last update timestamp |

### customers

Customer profiles linked to vehicles and conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Customer name |
| email | VARCHAR(255) | UNIQUE | Contact email |
| phone | VARCHAR(50) | | Phone number |
| created_at | TIMESTAMP | default now() | Creation timestamp |
| updated_at | TIMESTAMP | default now(), on update | Last update |

**Relationships**: vehicles (one-to-many), appointments (one-to-many), conversations (one-to-many)

### vehicles

Vehicle information linked to customers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| customer_id | UUID | FK -> customers.id (CASCADE) | Owner reference |
| brand | VARCHAR(100) | NOT NULL | Vehicle brand (e.g., VW, Honda) |
| model | VARCHAR(100) | NOT NULL | Vehicle model (e.g., T-Cross) |
| year | INTEGER | | Manufacturing year |
| vin | VARCHAR(50) | UNIQUE | Vehicle Identification Number |
| license_plate | VARCHAR(20) | | License plate number |
| created_at | TIMESTAMP | default now() | Creation timestamp |
| updated_at | TIMESTAMP | default now(), on update | Last update |

**Relationships**: service_history (one-to-many), appointments (one-to-many)

### service_history

Service records for vehicles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| vehicle_id | UUID | FK -> vehicles.id (CASCADE) | Vehicle reference |
| service_type | VARCHAR(100) | NOT NULL | Type of service performed |
| description | TEXT | | Service details |
| service_date | TIMESTAMP | | When service was performed |
| mileage | INTEGER | | Vehicle mileage at service |
| cost | NUMERIC(10,2) | | Service cost |
| status | VARCHAR(50) | default "completed" | Service status |
| created_at | TIMESTAMP | default now() | Record creation |

### appointments

Scheduled service appointments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| customer_id | UUID | FK -> customers.id (CASCADE) | Customer reference |
| vehicle_id | UUID | FK -> vehicles.id (SET NULL) | Vehicle reference |
| service_type | VARCHAR(100) | NOT NULL | Type of service |
| scheduled_date | TIMESTAMP | NOT NULL | Appointment date/time |
| notes | TEXT | | Additional notes |
| status | VARCHAR(50) | default "scheduled" | Appointment status |
| created_at | TIMESTAMP | default now() | Creation timestamp |
| updated_at | TIMESTAMP | default now(), on update | Last update |

### document_embeddings

RAG vector store for semantic search.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| content | TEXT | NOT NULL | Document chunk text |
| doc_metadata | JSONB | | Chunk metadata (source, page, etc.) |
| embedding | VECTOR(1536) | | Vector embedding (dimension depends on model) |
| source | VARCHAR(255) | | Source document name |
| document_type | VARCHAR(100) | | Type: manual, spec, guide, faq, troubleshoot |
| created_at | TIMESTAMP | default now() | Ingestion timestamp |

**Vector Search**:
```sql
-- Cosine similarity search
SELECT content, source, document_type,
       1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
FROM document_embeddings
WHERE document_type = :doc_type  -- optional filter
ORDER BY embedding <=> CAST(:query_embedding AS vector)
LIMIT :top_k;
```

**Note**: The `doc_metadata` column was renamed from `metadata` to avoid SQLAlchemy reserved name conflicts.

### conversations

Chat conversation history.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| session_id | VARCHAR(255) | NOT NULL, INDEX | Session identifier |
| customer_id | UUID | FK -> customers.id (SET NULL) | Customer reference |
| messages | JSONB | default [] | Conversation messages array |
| conversation_metadata | JSONB | default {} | Session metadata |
| created_at | TIMESTAMP | default now() | Creation timestamp |
| updated_at | TIMESTAMP | default now(), on update | Last update |

**Messages JSONB Structure**:
```json
[
  {"role": "user", "content": "What is the engine power?"},
  {"role": "assistant", "content": "The engine produces 150 HP..."}
]
```

---

## Migrations

### Alembic Setup

Configuration: `alembic.ini` (root directory)

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply all pending migrations
docker-compose exec api alembic upgrade head

# Rollback one migration
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history
```

### Initial Migration

File: `migrations/versions/884f77aacc9a_initial_migration.py`

Creates all 7 tables with pgvector extension enabled.

---

## Database Initialization

### PostgreSQL Init Script

File: `scripts/init_postgres.sql`

Runs on first container startup to enable pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Seed Sample Data

```bash
# Seed knowledge base with automotive documentation
docker-compose exec api python scripts/seed_knowledge_base.py

# Initialize sample customer/vehicle data
docker-compose exec api python scripts/init_db.py
```

---

## Connection Configuration

### Environment Variables

```bash
DATABASE_URL=postgresql://genai:genai_secret@postgres:5432/genai_auto
POSTGRES_USER=genai
POSTGRES_PASSWORD=genai_secret
POSTGRES_DB=genai_auto
```

### Connection Pool (SQLAlchemy)

Configured in `src/storage/database.py`:
- **Pool size**: 10
- **Max overflow**: 20
- **Pool pre-ping**: true (health checks)
- **Driver**: asyncpg (async operations)

---

## Backup & Restore

### Backup

```bash
# Full database backup
docker-compose exec postgres pg_dump -U genai genai_auto > backup_$(date +%Y%m%d).sql

# Backup specific table
docker-compose exec postgres pg_dump -U genai -t document_embeddings genai_auto > embeddings_backup.sql
```

### Restore

```bash
# Restore from backup
docker-compose exec -T postgres psql -U genai genai_auto < backup_20260209.sql
```

### Reset Database

```bash
# Drop and recreate (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d postgres
# Wait for postgres to be ready, then:
docker-compose up -d api
```

---

## Source Files

- Models: `src/storage/models.py`
- Database session: `src/storage/database.py`
- Migrations: `migrations/`
- Init script: `scripts/init_postgres.sql`
- Seed script: `scripts/seed_knowledge_base.py`
