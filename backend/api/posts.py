from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from models import OperationPost, Domain, BoardCategory, SourceKind
from db import get_db

router = APIRouter(prefix="/operation-posts", tags=["posts"])


MOCK_POSTS = [
    OperationPost(
        id=1,
        title="vLLM GPU 메모리 최적화 전략",
        category=BoardCategory.실전_운용,
        domain=Domain.로컬_LLM,
        score=95,
        source_kind=SourceKind.ai_synthesized,
        sources=["https://github.com/vllm-project/vllm/issues/1234"],
        updated_at=datetime.now(),
        summary="vLLM에서 GPU 메모리를 효율적으로 관리하는 방법. KV cache 크기 조정과 tensor parallel 설정이 핵심.",
        rule="--gpu-memory-utilization 0.9 이하로 설정하여 OOM 방지",
        action="vllm serve 시작 시 메모리 설정 확인 필수",
        tags=["vLLM", "GPU", "메모리", "최적화"],
        risk="high"
    ),
    OperationPost(
        id=2,
        title="Unity WebGL 빌드 크기 최적화",
        category=BoardCategory.깨알팁,
        domain=Domain.Unity,
        score=88,
        source_kind=SourceKind.manual_user_input,
        sources=["내부 문서"],
        updated_at=datetime.now(),
        summary="Unity WebGL 빌드 시 Brotli 압축과 Code Stripping으로 빌드 크기를 50% 이상 줄일 수 있음.",
        skill="Player Settings에서 Compression Format을 Brotli로 변경",
        action="릴리즈 빌드 전 압축 설정 확인",
        tags=["Unity", "WebGL", "최적화", "압축"],
        risk="low"
    ),
]


@router.get("", response_model=List[OperationPost])
async def get_operation_posts(
    domain: Optional[Domain] = Query(None),
    category: Optional[BoardCategory] = Query(None),
    source_kind: Optional[SourceKind] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    posts = MOCK_POSTS
    
    if domain:
        posts = [p for p in posts if p.domain == domain]
    if category:
        posts = [p for p in posts if p.category == category]
    if source_kind:
        posts = [p for p in posts if p.source_kind == source_kind]
    
    return posts[skip:skip + limit]


@router.get("/{post_id}", response_model=OperationPost)
async def get_operation_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    post = next((p for p in MOCK_POSTS if p.id == post_id), None)
    if not post:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    return post
