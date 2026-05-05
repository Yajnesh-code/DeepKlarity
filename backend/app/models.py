from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base, engine


JsonType = JSONB if engine.dialect.name == "postgresql" else JSON


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cuisine: Mapped[str] = mapped_column(String(100), default="Unknown")
    prep_time: Mapped[str] = mapped_column(String(80), default="")
    cook_time: Mapped[str] = mapped_column(String(80), default="")
    total_time: Mapped[str] = mapped_column(String(80), default="")
    servings: Mapped[int] = mapped_column(Integer, default=1)
    difficulty: Mapped[str] = mapped_column(String(30), default="medium")
    ingredients: Mapped[list] = mapped_column(JsonType, default=list)
    instructions: Mapped[list] = mapped_column(JsonType, default=list)
    nutrition_estimate: Mapped[dict] = mapped_column(JsonType, default=dict)
    substitutions: Mapped[list] = mapped_column(JsonType, default=list)
    shopping_list: Mapped[dict] = mapped_column(JsonType, default=dict)
    related_recipes: Mapped[list] = mapped_column(JsonType, default=list)
    scraped_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
