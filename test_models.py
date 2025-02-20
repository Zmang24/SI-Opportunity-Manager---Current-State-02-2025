from datetime import datetime
import uuid
from app.database.connection import SessionLocal
from app.models.models import User, Opportunity, AdasSystem, File, FileAttachment
from app.auth.auth_handler import hash_pin

def test_database_connection():
    """Test basic database operations with our models"""
    db = SessionLocal()
    try:
        print("Testing database connection and models...")
        
        # Create a test user
        test_user = User(
            username="test_user",
            email="test@example.com",
            pin=hash_pin("1234"),
            first_name="Test",
            last_name="User",
            team="QA",
            department="Engineering",
            role="user",
            is_active=True,
            notifications_enabled=True,
            created_at=datetime.utcnow()
        )
        
        # Add and commit the user
        db.add(test_user)
        db.flush()  # Flush to get the ID without committing
        print(f"Created test user with ID: {test_user.id}")
        
        # Create a test ADAS system
        test_system = AdasSystem(
            code="TEST-001",
            name="Test System",
            description="A test ADAS system",
            created_at=datetime.utcnow()
        )
        
        db.add(test_system)
        db.flush()
        print(f"Created test ADAS system with ID: {test_system.id}")
        
        # Create a test opportunity
        test_opportunity = Opportunity(
            title="Test Opportunity",
            description="A test opportunity",
            status="new",
            creator_id=test_user.id,
            year="2024",
            make="Test Make",
            model="Test Model",
            systems={"primary": "TEST-001"},
            affected_portions={"area": "front"},
            meta_data={"priority": "high"},
            created_at=datetime.utcnow()
        )
        
        db.add(test_opportunity)
        db.flush()
        print(f"Created test opportunity with ID: {test_opportunity.id}")

        # Test file handling
        print("\nTesting file handling:")
        
        # Create a test file
        test_file = File(
            opportunity_id=test_opportunity.id,
            uploader_id=test_user.id,
            name="test.txt",
            path="/uploads/test.txt",
            size=1024,
            mime_type="text/plain",
            hash="abc123",
            data=b"Test file content",
            created_at=datetime.utcnow()
        )
        
        db.add(test_file)
        db.flush()
        print(f"Created test file with ID: {test_file.id}")
        
        # Create a test file attachment
        test_attachment = FileAttachment(
            opportunity_id=test_opportunity.id,
            filename="test_attachment.pdf",
            file_type="application/pdf",
            file_path="/attachments/test.pdf",
            file_size=2048,
            uploaded_by_id=test_user.id,
            uploaded_at=datetime.utcnow()
        )
        
        db.add(test_attachment)
        db.flush()
        print(f"Created test file attachment with ID: {test_attachment.id}")
        
        # Test relationships
        print("\nTesting relationships:")
        print(f"Opportunity creator: {test_opportunity.creator.username}")
        print(f"User's created opportunities: {len(test_user.created_opportunities)}")
        print(f"Opportunity files: {len(test_opportunity.files)}")
        print(f"Opportunity file attachments: {len(test_opportunity.file_attachments)}")
        
        # Don't actually commit the test data
        print("\nRolling back test data...")
        db.rollback()
        print("Test completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error during testing: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database_connection() 