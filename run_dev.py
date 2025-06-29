#!/usr/bin/env python3
"""
Development server script for Golf Pickem League
"""
import subprocess
import sys

if __name__ == "__main__":
    print("🏌️  Starting Golf Pickem League Development Server")
    print("📍 Access the application at: http://localhost:5001")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run main.py directly
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Thanks for using Golf Pickem League!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
