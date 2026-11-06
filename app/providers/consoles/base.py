from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class InstalledTitle:
    platform: str
    identifier: Optional[str]
    title: str
    installed_version: Optional[str]
    content_type: str
    source: str
    path: str
    content_id: Optional[str] = None
    category: Optional[str] = None
    storage: Optional[str] = None

    def to_dict(self):
        return asdict(self)

class ConsoleProvider:
    provider_name = "base"
    def health(self): raise NotImplementedError
    def scan(self): raise NotImplementedError
