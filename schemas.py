from pydantic import BaseModel
from typing import Optional, Dict


class VkUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    deactivated: Optional[str]
    is_closed: Optional[bool]
    can_access_closed: Optional[bool]
    bdate: Optional[str]


class VkChatMember(BaseModel):
    member_id: int
    invited_by: int
    join_date: int
    is_admin: bool
    can_kick: bool


class VkMessage(BaseModel):
    id: int
    date: int
    peer_id: int
    from_id: int
    text: str
    random_id: int
    reply_message: Dict

