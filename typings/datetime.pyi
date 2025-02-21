from typing import Any, Optional, TypeVar

_T = TypeVar('_T')

MINYEAR: int
MAXYEAR: int

class timedelta:
    def __init__(
        self,
        days: float = ...,
        seconds: float = ...,
        microseconds: float = ...,
        milliseconds: float = ...,
        minutes: float = ...,
        hours: float = ...,
        weeks: float = ...
    ) -> None: ...
    
    days: int
    seconds: int
    microseconds: int
    
    @property
    def total_seconds(self) -> float: ...

class date:
    def __init__(self, year: int, month: int, day: int) -> None: ...
    @classmethod
    def today(cls) -> date: ...
    @classmethod
    def fromtimestamp(cls, timestamp: float) -> date: ...
    year: int
    month: int
    day: int
    
    def isoformat(self) -> str: ...
    def strftime(self, fmt: str) -> str: ...
    def __str__(self) -> str: ...
    def __format__(self, fmt: str) -> str: ...

class time:
    def __init__(
        self,
        hour: int = ...,
        minute: int = ...,
        second: int = ...,
        microsecond: int = ...,
        tzinfo: Optional[Any] = ...
    ) -> None: ...
    
    hour: int
    minute: int
    second: int
    microsecond: int
    tzinfo: Optional[Any]
    
    def isoformat(self) -> str: ...
    def strftime(self, fmt: str) -> str: ...
    def __str__(self) -> str: ...
    def __format__(self, fmt: str) -> str: ...

class datetime(date):
    def __init__(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = ...,
        minute: int = ...,
        second: int = ...,
        microsecond: int = ...,
        tzinfo: Optional[Any] = ...
    ) -> None: ...
    
    @classmethod
    def now(cls, tz: Optional[Any] = ...) -> datetime: ...
    @classmethod
    def fromtimestamp(cls, timestamp: float, tz: Optional[Any] = ...) -> datetime: ...
    @classmethod
    def strptime(cls, date_string: str, format: str) -> datetime: ...
    
    hour: int
    minute: int
    second: int
    microsecond: int
    tzinfo: Optional[Any]
    
    def date(self) -> date: ...
    def time(self) -> time: ...
    def timestamp(self) -> float: ...
    def isoformat(self, sep: str = ...) -> str: ...
    def strftime(self, fmt: str) -> str: ...
    def __str__(self) -> str: ...
    def __format__(self, fmt: str) -> str: ... 