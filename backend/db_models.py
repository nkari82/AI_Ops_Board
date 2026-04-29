from importlib import import_module

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, UniqueConstraint, func
from pgvector.sqlalchemy import Vector

try:
    Base = import_module("backend.db").Base
except ModuleNotFoundError:
    Base = import_module("db").Base


class CrawledPost(Base):
    __tablename__ = "crawled_posts"

    __table_args__ = (
        UniqueConstraint("url", name="uix_crawled_post_url"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    title_ko = Column(String(500))
    url = Column(String(1000), nullable=False)
    source = Column(String(2000), nullable=False)
    source_type = Column(String(100), nullable=False)
    content = Column(Text)
    score = Column(Integer, default=0)
    extra_data = Column(JSON)
    embedding = Column(Vector(1536))
    summary = Column(Text)
    summary_ko = Column(Text)
    domain = Column(String(500))
    category = Column(String(500))
    doc_type = Column(String(100))
    tech_stack = Column(JSON, default=list)


    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
