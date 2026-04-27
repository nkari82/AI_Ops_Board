from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, UniqueConstraint, func
from pgvector.sqlalchemy import Vector
from db import Base


class CrawledPost(Base):
    __tablename__ = "crawled_posts"

    __table_args__ = (
        UniqueConstraint("url", name="uix_crawled_post_url"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    source = Column(String(50), nullable=False)
    source_type = Column(String(20), nullable=False)
    content = Column(Text)
    score = Column(Integer, default=0)
    extra_data = Column(JSON)
    embedding = Column(Vector(1536))
    summary = Column(Text)
    domain = Column(String(50))
    category = Column(String(50))
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
