"""
Pydantic v1 / v2 compatibility base model and contracts package.
"""

from typing import Any
import pydantic
from pydantic import BaseModel

PYDANTIC_V2 = pydantic.__version__.startswith("2.")

if PYDANTIC_V2:
    from pydantic import ConfigDict

    class CompatBaseModel(BaseModel):
        """BaseModel with unified Pydantic v1 and v2 API and strict extra='forbid'."""

        model_config = ConfigDict(extra="forbid")

else:
    class CompatBaseModel(BaseModel):
        """BaseModel with unified Pydantic v1 and v2 API and strict extra='forbid'."""

        class Config:
            extra = "forbid"

        def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return self.dict(*args, **kwargs)

        def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
            return self.json(*args, **kwargs)

        @classmethod
        def model_validate(cls, obj: Any, *args: Any, **kwargs: Any):
            return cls.parse_obj(obj)


__all__ = ["CompatBaseModel"]
