"""SQLAlchemy ORM models."""

from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.storage.database import Base


class User(Base):
    """Application user model (for authentication)."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Customer(Base):
    """Customer profile model."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicles = relationship("Vehicle", back_populates="customer")
    appointments = relationship("Appointment", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class Vehicle(Base):
    """Vehicle model."""

    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"))
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer)
    vin = Column(String(50), unique=True)
    license_plate = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="vehicles")
    service_history = relationship("ServiceHistory", back_populates="vehicle")
    appointments = relationship("Appointment", back_populates="vehicle")


class ServiceHistory(Base):
    """Service history model."""

    __tablename__ = "service_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"))
    service_type = Column(String(100), nullable=False)
    description = Column(Text)
    service_date = Column(DateTime)
    mileage = Column(Integer)
    cost = Column(Numeric(10, 2))
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="service_history")


class Appointment(Base):
    """Scheduled appointment model."""

    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"))
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    service_type = Column(String(100), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    notes = Column(Text)
    status = Column(String(50), default="scheduled")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="appointments")
    vehicle = relationship("Vehicle", back_populates="appointments")


class DocumentEmbedding(Base):
    """Document embedding for RAG."""

    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content = Column(Text, nullable=False)
    doc_metadata = Column(JSONB)  # Renamed from 'metadata' (reserved name)
    embedding = Column(Vector(1536))
    source = Column(String(255))
    document_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    """Conversation history model."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    messages = Column(JSONB, default=list)
    conversation_metadata = Column(JSONB, default=dict)  # Renamed from 'metadata' (reserved name)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="conversations")
