from datetime import datetime
from functools import total_ordering
from typing import List, Tuple

from sqlalchemy import ARRAY, Boolean, Column, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from src.domain.entities.enums import PostTypeEnum, SentimentsEnum, SocialNetworkEnum, ReportCriticsEnum
from src.infra.db.base import Base

ThemeTuple = Tuple[str, str, str]  # 0: id  # 1: name  # 2: color

PostTuple = Tuple[
    int,  # 0: id
    str,  # 1: url_post
    str,  # 2: username_author
    datetime,  # 3: timestamp
    str,  # 4: message
    List[str],  # 5: images
    int,  # 6: likes
    int,  # 7: comments
    int,  # 8: shares
    int,  # 9: views
    SentimentsEnum,  # 10: sentiment
    List[ThemeTuple],  # 11: themes
    str,  # 12: name_author
    Boolean,  # 13: nsfw
    Float,  # 14: isPointOfAttention (now predicted_pa as float)
]


@total_ordering
class Post(Base):
    __tablename__ = "Post"

    id = Column(String, primary_key=True)
    time = Column(DateTime, primary_key=True)
    mongoId = Column(String, unique=True, index=True)
    socialNetwork = Column(Enum(SocialNetworkEnum), nullable=False)
    postType = Column(Enum(PostTypeEnum), nullable=False)
    urlPost = Column(String, nullable=False)
    userId = Column(String, nullable=False)
    nameAuthor = Column(String, nullable=False)
    usernameAuthor = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    profileImage = Column(String)
    images = Column(ARRAY(String), default=[])
    likes = Column(Integer, nullable=False)
    comments = Column(Integer, nullable=False)
    shares = Column(Integer, nullable=False)
    views = Column(Integer, nullable=False)
    isRelevant = Column(Boolean, default=True, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    words = Column(ARRAY(String), default=[])
    frequency = Column(ARRAY(Integer), default=[])
    sumary = Column(Text)
    tags = Column(ARRAY(String), default=[])
    title = Column(String)
    transcription = Column(Text)
    videoDuration = Column(Integer)
    videoComments = Column(ARRAY(String), default=[])
    isHighlighted = Column(Boolean, default=False, nullable=False)
    image_link_issue = Column(Boolean)
    s3_image_url = Column(String)
    s3_key = Column(String)
    sentiment = Column(Enum(SentimentsEnum), nullable=True)
    embedding_openclip_text = Column(String)  # Vector type - stored as string in SQLAlchemy
    embedding_openclip_image = Column(String)  # Vector type - stored as string in SQLAlchemy
    has_theme = Column(Boolean)
    nsfw = Column(Boolean)
    predicted_pa = Column(Float)
    pa_feedback = Column(Boolean)
    true_pa = Column(Float)
    predicted_cr = Column(Enum(ReportCriticsEnum))

    # Relationship to Subtheme via PostSubtheme association
    # Using explicit join conditions due to composite key (id, time) on Post
    subthemes = relationship(
        "Subtheme",
        secondary="PostSubtheme",
        primaryjoin="and_(Post.id==foreign(PostSubtheme.postId), Post.time==foreign(PostSubtheme.postTime))",
        secondaryjoin="Subtheme.id==foreign(PostSubtheme.subthemeId)",
        viewonly=True,
    )

    def __lt__(self, other: "Post") -> bool:  # type: ignore[name-defined]
        if not isinstance(other, Post):
            return NotImplemented
        return (-self.likes, -self.time.timestamp(), self.id) < (
            -other.likes,
            -other.time.timestamp(),
            other.id,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Post):
            return NotImplemented
        return self.id == other.id and self.time == other.time
