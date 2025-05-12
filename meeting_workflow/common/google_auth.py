import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Optional

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service() -> Optional[build]:
    """
    Get or create Google Calendar service instance with proper authentication.
    Returns None if authentication fails.
    """
    creds = None
    
    # Load existing credentials if available
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Refresh or create new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error creating Calendar service: {e}")
        return None 