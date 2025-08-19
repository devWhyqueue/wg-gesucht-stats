import csv
import datetime
from dataclasses import dataclass, fields
from typing import Iterable, Optional, Union


@dataclass(frozen=True)
class FlatAd:
    url: str
    published: datetime
    rent: int
    size: int
    district: str
    female_inhabitants: int
    male_inhabitants: int
    diverse_inhabitants: int
    total_inhabitants: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FlatAd):
            return False
        return self.url == other.url

    def __hash__(self) -> int:
        return hash(self.url)


@dataclass(frozen=True)
class FlatAdDetails:
    """
    Detailed information about a flat ad scraped from the detail page.
    """
    headline: Optional[str] = None
    description: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    available_from: Optional[datetime.date] = None
    available_until: Optional[datetime.date] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None


def to_csv(objects: Iterable[Union[FlatAd, FlatAdDetails]], output_path: str) -> None:
    """
    Export a list of dataclass objects to a CSV file.
    
    Args:
        objects: List of FlatAd or FlatAdDetails objects to export
        output_path: Path where the CSV file should be saved
    """
    if not objects:
        return
    
    # Get the first object to determine the dataclass type and field names
    first_object = next(iter(objects))
    fieldnames = [field.name for field in fields(first_object)]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for obj in objects:
            row_data = {}
            for field in fields(obj):
                value = getattr(obj, field.name)
                # Handle different data types for CSV output
                if value is None:
                    row_data[field.name] = ''
                elif isinstance(value, datetime.datetime):
                    row_data[field.name] = value.isoformat()
                elif isinstance(value, datetime.date):
                    row_data[field.name] = value.isoformat()
                else:
                    row_data[field.name] = value
            writer.writerow(row_data)