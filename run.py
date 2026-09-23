#!/usr/bin/env python3
"""Run the Relay Flask application.

This script starts the Flask development server.
Usage:
    python run.py
    
Environment variables:
    FLASK_ENV: Set to 'production' for production config (default: development)
    FLASK_DEBUG: Set to '1' to enable debug mode (default: 0 for production, 1 for development)
    JWT_SECRET_KEY: Secret key for JWT signing (REQUIRED in production)
    DATABASE_URL: Database connection string (default: sqlite:///secure_exchange.db)
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


def main():
    """Run the Flask application."""
    app = create_app()
    
    # Get debug mode from environment
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    # In production, bind to localhost only (use a WSGI server in front)
    # For development, bind to localhost
    host = '127.0.0.1'
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting Relay server on {host}:{port}")
    print(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
