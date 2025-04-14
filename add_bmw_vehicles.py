#!/usr/bin/env python
import sys
import os
import uuid
from datetime import datetime, timezone

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.models.models import Vehicle

def add_bmw_vehicles():
    """Add BMW vehicles to the database"""
    db = SessionLocal()
    
    try:
        # Define BMW vehicles to add
        bmw_vehicles = [
            # 2025 models
            {'year': '2025', 'make': 'BMW', 'model': 'X5'},
            {'year': '2025', 'make': 'BMW', 'model': 'X3'},
            {'year': '2025', 'make': 'BMW', 'model': '3 Series'},
            {'year': '2025', 'make': 'BMW', 'model': '5 Series'},
            {'year': '2025', 'make': 'BMW', 'model': '7 Series'},
            
            # 2024 models
            {'year': '2024', 'make': 'BMW', 'model': 'X5'},
            {'year': '2024', 'make': 'BMW', 'model': 'X3'},
            {'year': '2024', 'make': 'BMW', 'model': '3 Series'},
            {'year': '2024', 'make': 'BMW', 'model': '5 Series'},
            {'year': '2024', 'make': 'BMW', 'model': '7 Series'},
            
            # 2023 models
            {'year': '2023', 'make': 'BMW', 'model': 'X5'},
            {'year': '2023', 'make': 'BMW', 'model': 'X3'},
            {'year': '2023', 'make': 'BMW', 'model': '3 Series'},
            {'year': '2023', 'make': 'BMW', 'model': '5 Series'},
            {'year': '2023', 'make': 'BMW', 'model': '7 Series'},
        ]
        
        # Check for existing BMW vehicles to avoid duplicates
        existing_bmw = db.query(Vehicle).filter(Vehicle.make == 'BMW').all()
        existing_bmw_keys = {(v.year, v.make, v.model) for v in existing_bmw}
        
        # Add vehicles that don't already exist
        vehicles_added = 0
        for vehicle_data in bmw_vehicles:
            key = (vehicle_data['year'], vehicle_data['make'], vehicle_data['model'])
            if key not in existing_bmw_keys:
                # Create vehicle object
                vehicle = Vehicle(
                    id=uuid.uuid4(),
                    year=vehicle_data['year'],
                    make=vehicle_data['make'],
                    model=vehicle_data['model'],
                    is_custom=False,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Add to database
                db.add(vehicle)
                vehicles_added += 1
                print(f"Added: {vehicle_data['year']} {vehicle_data['make']} {vehicle_data['model']}")
        
        # Commit changes
        db.commit()
        print(f"Successfully added {vehicles_added} BMW vehicles to the database")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding BMW vehicles: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_bmw_vehicles() 