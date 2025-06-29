#!/usr/bin/env python3
"""
Debug script to test the change password functionality

NOTE: This feature is currently disabled and marked as "Coming Soon".
This script is being kept for future reference when the feature is implemented.
Running this script now will show the "Feature Coming Soon" page.
"""
import requests

BASE_URL = "http://localhost:5001"

def test_change_password():
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("=== Testing Change Password Flow (CURRENTLY DISABLED - COMING SOON) ===")
    
    # Step 1: Login directly (assuming user exists)
    print("\n1. Logging in...")
    login_data = {
        'username': 'testuser',
        'password': 'testpass123'
    }
    
    login_response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code != 302:  # Should redirect after successful login
        # User might not exist, let's create one
        print("Login failed. Creating a new user...")
        register_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        }
        
        register_response = session.post(f"{BASE_URL}/auth/register", data=register_data, allow_redirects=False)
        print(f"Registration status: {register_response.status_code}")
        
        if register_response.status_code != 302:  # Should redirect after successful registration
            print("Registration failed. Response content:")
            print(register_response.text[:500])
            return
            
        # Try login again
        login_response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
        print(f"Login retry status: {login_response.status_code}")
        
        if login_response.status_code != 302:
            print("Login still failed after registration")
            return
    
    print("Login successful!")
    
    # Step 2: Access change password page
    print("\n2. Accessing change password page...")
    change_pw_page = session.get(f"{BASE_URL}/profile/change-password")
    print(f"Change password page status: {change_pw_page.status_code}")
    
    if change_pw_page.status_code != 200:
        print("Could not access change password page")
        print(change_pw_page.text[:500])
        return
    
    # Step 3: Submit change password form
    print("\n3. Submitting change password form...")
    change_pw_data = {
        'current_password': 'testpass123',
        'new_password': 'newpass123',
        'confirm_password': 'newpass123'
    }
    
    try:
        change_pw_response = session.post(f"{BASE_URL}/profile/change-password", data=change_pw_data, allow_redirects=False)
        print(f"Change password response status: {change_pw_response.status_code}")
        
        # If we got a 200 response, check the content
        if change_pw_response.status_code == 200:
            if "Password Changed Successfully" in change_pw_response.text:
                print("Password change was successful!")
            else:
                print("Password change failed. Response content:")
                print(change_pw_response.text)
                # Check for specific error messages
                error_phrases = ["Current password is incorrect", "New passwords do not match", 
                                 "Form data error", "at least 8 characters"]
                for phrase in error_phrases:
                    if phrase in change_pw_response.text:
                        print(f"Error found: '{phrase}'")
                        break
        else:
            print("Unexpected response code")
            print(change_pw_response.text[:500])
    except Exception as e:
        print(f"Error submitting change password: {e}")

if __name__ == "__main__":
    test_change_password()
