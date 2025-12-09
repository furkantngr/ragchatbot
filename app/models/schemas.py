from pydantic import BaseModel
from typing import List, Dict, Any

class Question(BaseModel):
    query: str
    mode: str = "fast" # <-- YENİ: "fast" veya "thinking" olabilir
    history: List[Dict[str, Any]] = []

class Answer(BaseModel):
    response: str