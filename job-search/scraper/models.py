from dataclasses import dataclass, asdict


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    date_posted: str
    description: str
    keyword: str
    region: str
    scraped_at: str

    def to_dict(self) -> dict:
        return asdict(self)
