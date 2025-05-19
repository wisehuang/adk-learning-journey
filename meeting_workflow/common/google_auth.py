import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Optional
from google.cloud import secretmanager
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """
    Access the secret version from Secret Manager.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_calendar_service(project_id: str) -> Optional[build]:
    """
    Get or create Google Calendar service instance with proper authentication.
    Uses Secret Manager for credentials and token storage.
    Returns None if authentication fails.
    """
    creds = None
    
    try:
        # Try to get token from Secret Manager
        token_json = get_secret(project_id, "calendar-token")
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    except Exception as e:
        print(f"Could not load token from Secret Manager: {e}")
    
    # Refresh or create new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                # Get credentials from Secret Manager
                credentials_json = get_secret(project_id, "calendar-credentials")
                flow = InstalledAppFlow.from_client_config(
                    json.loads(credentials_json), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Error loading credentials from Secret Manager: {e}")
                raise
        
        # Save new token to Secret Manager
        try:
            client = secretmanager.SecretManagerServiceClient()
            parent = f"projects/{project_id}/secrets/calendar-token"
            token_data = creds.to_json()
            client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": token_data.encode("UTF-8")}
                }
            )
        except Exception as e:
            print(f"Error saving token to Secret Manager: {e}")
    
    try:
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error creating Calendar service: {e}")
        return None 