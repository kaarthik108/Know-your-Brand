#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db_manager
import uuid

def test_database_connection():
    """Test the database connection and basic operations"""
    
    print("Testing database connection...")
    
    try:
        # Test 1: Initialize tables
        print("1. Initializing tables...")
        db_manager.init_tables()
        print("✓ Tables initialized successfully")
        
        # Test 2: Create a test request
        print("2. Creating test request...")
        test_user_id = "test_user_123"
        test_session_id = "test_session_456"
        test_brand_name = "TestBrand"
        
        request_id = db_manager.create_request(test_user_id, test_session_id, test_brand_name)
        print(f"✓ Request created with ID: {request_id}")
        
        # Test 3: Get request status
        print("3. Getting request status...")
        status = db_manager.get_request_status(test_user_id, test_session_id)
        print(f"✓ Status retrieved: {status['status']}")
        
        # Test 4: Update status
        print("4. Updating status to 'running'...")
        db_manager.update_status(test_user_id, test_session_id, "running")
        
        status = db_manager.get_request_status(test_user_id, test_session_id)
        print(f"✓ Status updated to: {status['status']}")
        
        # Test 5: Save results
        print("5. Saving test results...")
        test_results = {
            "userId": test_user_id,
            "sessionId": test_session_id,
            "brand_name": test_brand_name,
            "analysis_results_twitter": {"test": "data"},
            "analysis_results_linkedin": {"test": "data"},
            "analysis_results_reddit": {"test": "data"},
            "analysis_results_news": {"test": "data"}
        }
        
        db_manager.save_results(test_user_id, test_session_id, test_results)
        
        final_status = db_manager.get_request_status(test_user_id, test_session_id)
        print(f"✓ Results saved, final status: {final_status['status']}")
        
        # Test 6: Cleanup test data
        print("6. Cleaning up test data...")
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM brand_analysis_requests WHERE user_id = %s AND session_id = %s",
                    (test_user_id, test_session_id)
                )
                conn.commit()
        print("✓ Test data cleaned up")
        
        print("\n🎉 All database tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1) 