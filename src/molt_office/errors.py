from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WorldError(Exception):
    code: str
    message: str
    detail: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class SystemError(Exception):
    pass
