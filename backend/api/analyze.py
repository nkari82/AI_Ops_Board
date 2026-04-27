from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from models import AnalyzeRequest

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("")
async def analyze_content(request: AnalyzeRequest) -> Dict[str, Any]:
    try:
        from ..services.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        
        result = await analyzer.analyze(
            content=request.content,
            source_url=request.source_url,
            domain=request.domain
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
