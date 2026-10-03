from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

from app.schemas.treasury import AgentFinding


class TreasuryAgent(ABC):
    name: str

    @abstractmethod
    def run(self, db: Session) -> list[AgentFinding]:
        raise NotImplementedError
