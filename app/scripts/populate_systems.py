import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from app.models import SessionLocal, AdasSystem

ADAS_SYSTEMS = [
    {
        'code': 'ACC 1',
        'name': 'Adaptive Cruise Control (1)',
        'description': 'Any intelligent cruise control that uses ONLY front radar(s) to operate.'
    },
    {
        'code': 'ACC 2',
        'name': 'Adaptive Cruise Control (2)',
        'description': 'Any intelligent cruise control that uses BOTH the windshield camera and front radar(s) to operate.'
    },
    {
        'code': 'ACC 3',
        'name': 'Adaptive Cruise Control (3)',
        'description': 'Any intelligent cruise control that uses ONLY the windshield camera to operate.'
    },
    {
        'code': 'AEB 1',
        'name': 'Automatic Emergency Braking (1)',
        'description': 'Any collision mitigation that uses ONLY front radar(s) to operate.'
    },
    {
        'code': 'AEB 2',
        'name': 'Automatic Emergency Braking (2)',
        'description': 'Any collision mitigation that uses BOTH the windshield camera and front radar(s) to operate.'
    },
    {
        'code': 'AEB 3',
        'name': 'Automatic Emergency Braking (3)',
        'description': 'Any collision mitigation that uses ONLY the windshield camera to operate.'
    },
    {
        'code': 'AHL',
        'name': 'Adaptive Head Lamps',
        'description': 'Any front lighting systems that adapt to the direction of travel as the steering is moved.'
    },
    {
        'code': 'APA',
        'name': 'Active Parking Assistance',
        'description': 'All parking aid bumper sensors (front and/or back) that REQUIRE calibration.'
    },
    {
        'code': 'APA 1',
        'name': 'Active Parking Assistance (1)',
        'description': 'Front AND Rear parking aid bumper sensors that REQUIRE calibration.'
    },
    {
        'code': 'APA 2',
        'name': 'Active Parking Assistance (2)',
        'description': 'Rear ONLY parking aid bumper sensors that REQUIRE calibration.'
    },
    {
        'code': 'BSW-RCTW 1',
        'name': 'Blind Spot Warning/Rear Cross Traffic Warning (1)',
        'description': 'Any side monitoring system located in the rear of the vehicle.'
    },
    {
        'code': 'BSW-RCTW 2',
        'name': 'Blind Spot Warning/Rear Cross Traffic Warning (2)',
        'description': 'Blind Spot Warning systems that are housed in the rear taillights.'
    },
    {
        'code': 'BSW-RCTW 3',
        'name': 'Blind Spot Warning/Rear Cross Traffic Warning (3)',
        'description': 'Blind Spot Warning system that is operated through the rearview camera.'
    },
    {
        'code': 'BUC',
        'name': 'Backup Camera',
        'description': 'Any parking aid camera system that ONLY includes the rear camera.'
    },
    {
        'code': 'LKA 1',
        'name': 'Lane Keeping Assistance (1)',
        'description': 'Any front windshield camera system that alerts/assists with keeping the vehicle in the driving lane(s).'
    },
    {
        'code': 'LKA 2',
        'name': 'Lane Keeping Assistance (2)',
        'description': 'Any system that alerts/assists with keeping the vehicle in the driving lane(s) that uses the REAR camera to operate.'
    },
    {
        'code': 'LW',
        'name': 'Lane Watch',
        'description': '(Honda Specific) Passenger mirror camera.'
    },
    {
        'code': 'NV',
        'name': 'Night Vision',
        'description': 'Night Vision camera systems.'
    },
    {
        'code': 'SVC',
        'name': 'Surround View Camera',
        'description': 'Any multi-camera parking aid system.'
    },
    {
        'code': 'SVC 1',
        'name': 'Surround View Camera (1)',
        'description': 'ANY 4 Camera Parking aid system.'
    },
    {
        'code': 'SVC 2',
        'name': 'Surround View Camera (2)',
        'description': 'ANY 2 Camera Parking aid system that uses a Front and Rear Camera only.'
    },
    {
        'code': 'SVC 3',
        'name': 'Surround View Camera (3)',
        'description': 'ANY 2 Camera Parking System that uses a Driver and Passenger Camera only.'
    },
    {
        'code': 'SVC 4',
        'name': 'Surround View Camera (4)',
        'description': 'ANY 3 Camera Parking System that uses Side AND Rear Cameras only.'
    }
]

def populate_systems():
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(AdasSystem).delete()
        db.commit()
        
        # Add new systems
        for system in ADAS_SYSTEMS:
            adas_system = AdasSystem(
                code=system['code'],
                name=system['name'],
                description=system['description']
            )
            db.add(adas_system)
        
        db.commit()
        print("Successfully populated ADAS systems!")
        
    except Exception as e:
        print(f"Error populating ADAS systems: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_systems() 