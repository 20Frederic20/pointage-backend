from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainErrorSchema(BaseModel):
    """Wire schema for a domain error response (mirrors ``DomainError``).

    Field names are snake_case in Python; camelCase aliases keep the JSON wire
    contract stable (``model_dump(by_alias=True)``).
    """

    is_domain_error: bool = Field(default=True, alias="isDomainError")
    name: str
    code: str
    message: str
    severity: str
    context: str = ""
    http_status: int = Field(alias="httpStatus")
    occurred_at: datetime = Field(alias="occurredAt")

    model_config = ConfigDict(populate_by_name=True)
