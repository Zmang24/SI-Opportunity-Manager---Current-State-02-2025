# This file marks the directory as a Python package
from .models.models import User, Opportunity, Vehicle, AdasSystem
from .models import Base, SessionLocal, engine

__all__ = [
    'Base',
    'SessionLocal',
    'engine',
    'User',
    'Opportunity',
    'Vehicle',
    'AdasSystem'
]

# This makes the app directory a Python package 