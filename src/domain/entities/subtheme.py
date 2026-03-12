import uuid

from sqlalchemy import ARRAY, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from src.infra.db.base import Base


class Subtheme(Base):
    __tablename__ = "Subtheme"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    themeId = Column(String, ForeignKey("Theme.id"), nullable=True)
    validTerms = Column(ARRAY(String), default=[])

    theme = relationship("Theme", back_populates="subthemes")
    post_subthemes = relationship("PostSubtheme", back_populates="subtheme")