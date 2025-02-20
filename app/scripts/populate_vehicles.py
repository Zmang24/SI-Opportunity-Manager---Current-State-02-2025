import csv
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from app.models import SessionLocal, Vehicle

def populate_vehicles():
    db = SessionLocal()
    try:
        # Read the CSV file
        csv_path = Path(root_dir) / 'VehicleDataSheet.csv'
        
        if not csv_path.exists():
            print(f"Error: Vehicle data file not found at {csv_path}")
            return
            
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            # First, let's check the CSV structure
            sample = file.readline()
            file.seek(0)  # Reset to start of file
            
            if ',' in sample:
                delimiter = ','
            elif ';' in sample:
                delimiter = ';'
            else:
                delimiter = None
            
            csv_reader = csv.DictReader(file, delimiter=delimiter)
            
            # Get the actual fieldnames from the CSV
            fieldnames = csv_reader.fieldnames
            print(f"Found CSV columns: {fieldnames}")
            
            # Track unique combinations to avoid duplicates
            existing_vehicles = set()
            added_count = 0
            
            for row in csv_reader:
                try:
                    # Try to get year, make, model from the CSV columns
                    year = int(str(row.get('Year', '')).strip())  # Convert to integer
                    make = str(row.get('Make', '')).strip()
                    model = str(row.get('Model', '')).strip()
                    
                    # Skip if missing required data
                    if not all([year, make, model]):
                        print(f"Skipping row due to missing data: {row}")
                        continue
                        
                    # Create unique key for vehicle
                    vehicle_key = (year, make, model)
                    
                    # Skip if we've already added this vehicle
                    if vehicle_key in existing_vehicles:
                        continue
                        
                    existing_vehicles.add(vehicle_key)
                    
                    # Create new vehicle entry
                    vehicle = Vehicle(
                        year=year,
                        make=make,
                        model=model,
                        is_custom=False
                    )
                    
                    # Print what we're about to add
                    print(f"Adding vehicle: Year={vehicle.year}, Make={vehicle.make}, Model={vehicle.model}")
                    
                    db.add(vehicle)
                    added_count += 1
                    
                    # Commit every 100 vehicles to avoid memory issues
                    if added_count % 100 == 0:
                        db.commit()
                        print(f"Added {added_count} vehicles...")
                    
                except Exception as e:
                    print(f"Error processing row {row}: {str(e)}")
                    continue
            
            # Final commit for remaining vehicles
            db.commit()
            print(f"\nSuccessfully populated vehicle data! Added {added_count} unique vehicles.")
            
            # Query and print a few vehicles to verify data
            print("\nVerifying data in database:")
            vehicles = db.query(Vehicle).limit(5).all()
            for v in vehicles:
                print(f"Vehicle record: Year={v.year}, Make={v.make}, Model={v.model}")
            
    except Exception as e:
        print(f"Error populating vehicle data: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_vehicles() 