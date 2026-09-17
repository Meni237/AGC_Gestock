from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Nouveau modèle pour les articles
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    quantity = Column(Integer, default=0)
    min_quantity = Column(Integer, default=5)  # Seuil pour alerte stock bas
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)