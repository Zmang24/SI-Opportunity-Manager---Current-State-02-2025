import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text
from app.database.connection import SessionLocal
from app.models.models import User, Opportunity, ActivityLog, Notification, File, FileAttachment

def check_users_table():
    """Check the number of users in the users table"""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        print(f"Number of users in database: {user_count}")
        return user_count
    finally:
        db.close()

def clear_all_tables():
    """Clear all related tables in the correct order to handle foreign key constraints"""
    db = SessionLocal()
    try:
        # Delete in order of dependencies
        print("Deleting file attachments...")
        deleted_count = db.query(FileAttachment).delete()
        print(f"Deleted {deleted_count} file attachments")
        
        print("Deleting files...")
        deleted_count = db.query(File).delete()
        print(f"Deleted {deleted_count} files")
        
        print("Deleting notifications...")
        deleted_count = db.query(Notification).delete()
        print(f"Deleted {deleted_count} notifications")
        
        print("Deleting activity logs...")
        deleted_count = db.query(ActivityLog).delete()
        print(f"Deleted {deleted_count} activity logs")
        
        print("Deleting opportunities...")
        deleted_count = db.query(Opportunity).delete()
        print(f"Deleted {deleted_count} opportunities")
        
        print("Deleting users...")
        deleted_count = db.query(User).delete()
        print(f"Deleted {deleted_count} users")
        
        db.commit()
        print("All related tables cleared successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error clearing tables: {str(e)}")
        raise
    finally:
        db.close()

def list_users():
    """List all users in the database"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\nCurrent Users:")
        print("-------------")
        for user in users:
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"Team: {user.team}")
            print(f"Department: {user.department}")
            print(f"Active: {user.is_active}")
            print("-------------")
        return users
    finally:
        db.close()

if __name__ == "__main__":
    # When run directly, this will clear all tables
    print("Checking users table...")
    initial_count = check_users_table()
    
    if initial_count > 0:
        response = input("Do you want to delete all users and related data? (yes/no): ")
        if response.lower() == 'yes':
            clear_all_tables()
            print("\nVerifying users table is empty...")
            final_count = check_users_table()
            assert final_count == 0, "Users table should be empty"
        else:
            print("Operation cancelled")
    else:
        print("Users table is already empty") 