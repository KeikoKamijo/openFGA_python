from sqlalchemy import Column, Integer, String
from config import Base
import uuid


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    owner = Column(String(255), nullable=False)