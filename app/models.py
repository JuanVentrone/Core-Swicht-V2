from dataclasses import dataclass


@dataclass
class Contactor:
    name: str
    id: str
    ip: str
    key: str
    version: str = "3.4"
