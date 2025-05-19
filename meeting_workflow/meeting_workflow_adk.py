#!/usr/bin/env python3
"""
Meeting Workflow ADK Implementation
Multi-agent meeting scheduling system using Google ADK framework
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Google ADK core imports
from google.adk.tools import BaseTool
from google.adk.agents import Agent, SequentialAgent

# Calendar API related imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Get project ID from environment variable
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")

def get_calendar_service():
    """Get authorized Google Calendar service"""
    from common.google_auth import get_calendar_service as get_service
    return get_service(PROJECT_ID)

# Define ADK Tool - Attendee Validator Tool
class ValidateAttendeesTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="validate_attendees",
            description="Validate attendee email formats and permissions"
        )
    
    def execute(self, context, attendees: list):
        """Validate attendee email formats"""
        invalid_emails = []
        for email in attendees:
            if '@' not in email or '.' not in email:
                invalid_emails.append(email)
                
        if invalid_emails:
            return {"valid": False, "invalid_emails": invalid_emails}
        return {"valid": True}

# Define ADK Tool - Meeting Scheduler Tool
class ScheduleMeetingTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="schedule_meeting",
            description="Schedule meetings in Google Calendar, handle conflicts and attendee notifications"
        )
    
    def execute(self, context, summary: str, start_time: str, 
               duration_min: int, attendees: list, description: str = None):
        """Schedule meetings and handle conflicts"""
        try:
            # Initialize calendar service
            service = get_calendar_service()
            
            # Time format conversion
            try:
                # Try to parse the provided time
                start = datetime.fromisoformat(start_time)
            except ValueError as e:
                logger.warning(f"Invalid start time format: {start_time}. Using default.")
                # Default to tomorrow at 2 PM
                start = datetime.now() + timedelta(days=1)
                start = start.replace(hour=14, minute=0, second=0, microsecond=0)
            
            end = start + timedelta(minutes=duration_min)
            
            # Create event structure
            event = {
                'summary': summary or "Untitled Meeting",
                'start': {
                    'dateTime': start.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': 'Asia/Taipei'
                },
                'end': {
                    'dateTime': end.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': 'Asia/Taipei'
                }
            }
            
            # Ensure valid attendees
            valid_attendees = []
            for email in attendees:
                if '@' in email and '.' in email:
                    valid_attendees.append({'email': email})
            
            if valid_attendees:
                event['attendees'] = valid_attendees
            
            if description:
                event['description'] = description
            
            # Check for conflicts
            try:
                # Ensure emails are valid and properly formatted for API
                calendar_items = []
                for email in attendees:
                    if '@' in email and '.' in email:
                        calendar_items.append({"id": email})
                
                if not calendar_items:
                    # If no valid emails, skip conflict check
                    logger.warning("No valid emails for conflict check")
                    conflicts = []
                else:
                    # Ensure timezone information is included
                    start_str = start.strftime('%Y-%m-%dT%H:%M:%S%z')
                    end_str = end.strftime('%Y-%m-%dT%H:%M:%S%z')
                    
                    # If no timezone info, add Z for UTC
                    if '+' not in start_str and '-' not in start_str:
                        start_str = start.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                        end_str = end.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                    
                    freebusy = service.freebusy().query(body={
                        "timeMin": start_str,
                        "timeMax": end_str,
                        "items": calendar_items,
                        "timeZone": "Asia/Taipei"
                    }).execute()
                    
                    # Handle conflicts
                    conflicts = []
                    for attendee, data in freebusy.get('calendars', {}).items():
                        if data.get('busy', []):
                            conflicts.append(attendee)
            except HttpError as error:
                logger.error(f"Calendar API error in conflict check: {error}")
                # Continue with empty conflicts list on error
                conflicts = []
            except Exception as e:
                logger.error(f"Unexpected error in conflict check: {e}")
                conflicts = []
            
            if conflicts:
                alternative_times = self._find_alternative_times(service, start, duration_min, attendees)
                return {
                    "status": "conflict",
                    "message": f"Attendees with conflicts: {', '.join(conflicts)}",
                    "suggestions": alternative_times
                }
            
            # Create event
            created_event = service.events().insert(
                calendarId='primary', 
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "status": "success", 
                "event_id": created_event['id'],
                "message": "Meeting has been scheduled and notifications sent"
            }
            
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            return {"status": "error", "message": f"API Error: {str(error)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    
    def _find_alternative_times(self, service, original_start, duration, attendees):
        """Intelligently find alternative time options"""
        alternatives = []
        current = original_start
        end_range = original_start + timedelta(days=3)
        
        # Ensure attendees are valid
        calendar_items = []
        for email in attendees:
            if '@' in email and '.' in email:
                calendar_items.append({"id": email})
        
        if not calendar_items:
            # If no valid emails, return empty alternatives
            logger.warning("No valid emails for alternative time check")
            return alternatives
        
        while current < end_range and len(alternatives) < 5:
            # Only search during working hours
            if 9 <= current.hour < 18 and current.weekday() < 5:
                end_time = current + timedelta(minutes=duration)
                try:
                    # Ensure timezone information is included
                    start_str = current.strftime('%Y-%m-%dT%H:%M:%S%z')
                    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S%z')
                    
                    # If no timezone info, add Z for UTC
                    if '+' not in start_str and '-' not in start_str:
                        start_str = current.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                    
                    freebusy = service.freebusy().query(body={
                        "timeMin": start_str,
                        "timeMax": end_str,
                        "items": calendar_items,
                        "timeZone": "Asia/Taipei"
                    }).execute()
                    
                    all_available = True
                    for _, data in freebusy.get('calendars', {}).items():
                        if data.get('busy', []):
                            all_available = False
                            break
                    
                    if all_available:
                        alternatives.append(current.isoformat())
                except HttpError as error:
                    logger.warning(f"API error while checking alternative time: {error}")
                except Exception as e:
                    logger.warning(f"Error during alternative time check: {e}")
            
            current += timedelta(minutes=30)  # Check every 30 minutes
        
        return alternatives

# Define ADK Tool - Meeting Notification Tool
class SendMeetingNotificationTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="send_meeting_notification",
            description="Generate and send meeting notifications to all attendees"
        )
    
    def execute(self, context, event_id: str, summary: str, start_time: str, 
                duration_min: int, attendees: list, description: str = None, 
                is_update: bool = False, is_cancellation: bool = False):
        """Generate and send meeting notifications"""
        try:
            # Organize time information
            try:
                # Try to parse the provided time
                start = datetime.fromisoformat(start_time)
            except ValueError as e:
                logger.warning(f"Invalid start time format: {start_time}. Using default.")
                # Default to tomorrow at 2 PM
                start = datetime.now() + timedelta(days=1)
                start = start.replace(hour=14, minute=0, second=0, microsecond=0)
                
            end = start + timedelta(minutes=duration_min)
            
            # Determine notification type
            notification_type = "Meeting Invitation"
            if is_update:
                notification_type = "Meeting Update"
            elif is_cancellation:
                notification_type = "Meeting Cancellation"
            
            # Generate notification content
            notification = self._generate_notification(
                notification_type=notification_type,
                summary=summary,
                start=start,
                end=end,
                description=description
            )
            
            # In a real implementation, this would connect to an email service or other notification system
            # This is just simulating notification sending
            logger.info(f"Sending {notification_type} to {', '.join(attendees)}")
            logger.info(f"Notification content:\n{notification}")
            
            # If integrated with Google Calendar API, you could call the following code
            if not is_cancellation and not is_update:
                # This part is already handled in the schedule_meeting tool, this is just for demonstration
                """
                service = get_calendar_service()
                service.events().insert(
                    calendarId='primary',
                    body=event,
                    sendUpdates='all'
                ).execute()
                """
                pass
            
            return {
                "status": "success",
                "message": f"{notification_type} has been sent to all attendees",
                "recipients": attendees,
                "event_id": event_id
            }
            
        except Exception as e:
            logger.error(f"Notification sending error: {e}")
            return {
                "status": "error",
                "message": f"Failed to send notification: {str(e)}"
            }
    
    def _generate_notification(self, notification_type, summary, start, end, description=None):
        """Generate formatted notification content"""
        template = f"""
        {notification_type}
        ===================
        
        Subject: {summary}
        Time: {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}
        Location: Google Meet (link will be sent before the meeting)
        
        {description or 'No description provided'}
        
        Please confirm your attendance status.
        """
        return template

# Define agents
def create_agents():
    """Create multi-agent system"""
    # Validator agent
    validate_agent = Agent(
        name="attendee_validator",
        model="gemini-2.5-pro-preview-05-06",
        tools=[ValidateAttendeesTool()],
        instruction="Validate meeting attendee email formats, ensure all addresses follow standard format"
    )
    
    # Scheduler agent
    scheduling_agent = Agent(
        name="meeting_scheduler", 
        model="gemini-2.5-pro-preview-05-06",
        tools=[ScheduleMeetingTool()],
        instruction="Handle meeting scheduling and conflict resolution, find optimal meeting times"
    )
    
    # Notification agent
    notification_agent = Agent(
        name="notification_sender",
        model="gemini-2.5-pro-preview-05-06",
        tools=[SendMeetingNotificationTool()],
        instruction="Generate meeting notification content and send to participants, ensure all messages are clear"
    )
    
    # Use SequentialAgent to assemble workflow
    meeting_workflow = SequentialAgent(
        name="meeting_workflow",
        sub_agents=[
            validate_agent,
            scheduling_agent,
            notification_agent
        ]
    )
    
    return meeting_workflow

def process_meeting_request(context):
    """Process meeting request"""
    workflow = create_agents()
    
    # Call the agents individually since SequentialAgent doesn't have a run method
    # Step 1: Validate attendees
    attendees = extract_attendees(context["query"])
    validator = workflow.sub_agents[0]
    validation_input = f"Validate these attendees: {', '.join(attendees)}"
    
    # Use the tool directly instead of going through the agent
    validation_tool = ValidateAttendeesTool()
    validation_result = validation_tool.execute({}, attendees)
    
    if not validation_result.get("valid", False):
        return {
            "status": "error",
            "message": "Attendee email validation failed",
            "details": validation_result
        }
    
    # Step 2: Schedule meeting - Extract details and call tool directly
    meeting_details = extract_meeting_details(context["query"])
    scheduler_tool = ScheduleMeetingTool()
    scheduling_result = scheduler_tool.execute(
        {},
        summary=meeting_details.get("summary", "Meeting"),
        start_time=meeting_details.get("start_time", ""),
        duration_min=meeting_details.get("duration_min", 60),
        attendees=attendees,
        description=meeting_details.get("description", "")
    )
    
    if scheduling_result.get("status") != "success":
        return scheduling_result
    
    # Step 3: Send notifications - Use the notification tool directly
    notifier_tool = SendMeetingNotificationTool()
    notification_result = notifier_tool.execute(
        {},
        event_id=scheduling_result.get("event_id", "unknown"),
        summary=meeting_details.get("summary", "Meeting"),
        start_time=meeting_details.get("start_time", ""),
        duration_min=meeting_details.get("duration_min", 60),
        attendees=attendees,
        description=meeting_details.get("description", "")
    )
    
    return {
        "status": "success",
        "message": "Meeting has been scheduled and notifications sent",
        "details": {
            "validation": validation_result,
            "scheduling": scheduling_result,
            "notification": notification_result
        }
    }

def extract_meeting_details(query):
    """Extract meeting details from query"""
    details = {
        "summary": "",
        "start_time": "",
        "duration_min": 60,
        "description": ""
    }
    
    # Default to tomorrow at 2 PM
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    details["start_time"] = tomorrow.isoformat()
    
    lines = query.split('\n')
    for line in lines:
        line = line.strip()
        if ('subject' in line.lower() or 'topic' in line.lower() or 'title' in line.lower()) and ':' in line:
            details["summary"] = line.split(':', 1)[1].strip()
        elif 'time' in line.lower() and ':' in line:
            time_text = line.split(':', 1)[1].strip()
            # Try different formats
            if 'T' in time_text:  # ISO format with T separator
                try:
                    datetime.fromisoformat(time_text)
                    details["start_time"] = time_text
                except ValueError:
                    pass
            elif '-' in time_text and ':' in time_text:
                # Try to parse date-time format like "2023-05-15 14:00"
                try:
                    dt = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
                    details["start_time"] = dt.isoformat()
                except ValueError:
                    try:
                        # Try with seconds
                        dt = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S")
                        details["start_time"] = dt.isoformat()
                    except ValueError:
                        pass
        elif ('duration' in line.lower() or 'length' in line.lower()) and ':' in line:
            duration_text = line.split(':', 1)[1].strip()
            try:
                # Extract the numeric part
                import re
                duration_match = re.search(r'\d+', duration_text)
                if duration_match:
                    details["duration_min"] = int(duration_match.group())
            except ValueError:
                pass
        elif ('description' in line.lower() or 'notes' in line.lower()) and ':' in line:
            details["description"] = line.split(':', 1)[1].strip()
    
    # Final validation of start_time
    try:
        # Try to parse it to confirm it's valid
        datetime.fromisoformat(details["start_time"])
    except ValueError:
        # If still invalid, reset to default
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        details["start_time"] = tomorrow.isoformat()
    
    return details

def extract_attendees(query):
    """Extract attendee email addresses from query"""
    lines = query.split('\n')
    for line in lines:
        if ('attendees' in line.lower() or 'participants' in line.lower()) and ':' in line:
            # Extract the part after the colon, split by comma
            attendees_part = line.split(':', 1)[1].strip()
            return [email.strip() for email in attendees_part.split(',')]
    return []

# Example main program
if __name__ == "__main__":
    # Parse input parameters
    import argparse
    parser = argparse.ArgumentParser(description='ADK Meeting Scheduling System')
    parser.add_argument('--summary', type=str, help='Meeting subject')
    parser.add_argument('--time', type=str, help='Start time (ISO format)')
    parser.add_argument('--duration', type=int, default=60, help='Meeting duration (minutes)')
    parser.add_argument('--attendees', type=str, help='Attendees (comma separated)')
    parser.add_argument('--description', type=str, help='Meeting description')
    args = parser.parse_args()
    
    # If command line parameters are not provided, use example parameters
    if not all([args.summary, args.time, args.attendees]):
        print("Using example parameters...")
        # Tomorrow at 2 PM
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        
        context = {
            "query": f"""Schedule meeting:
            Subject: Product Development Meeting
            Time: {tomorrow.isoformat()}
            Duration: 60 minutes
            Attendees: alice@example.com, bob@example.com
            Description: Discuss next quarter product development plans"""
        }
    else:
        context = {
            "query": f"""Schedule meeting:
            Subject: {args.summary}
            Time: {args.time}
            Duration: {args.duration} minutes
            Attendees: {args.attendees}
            Description: {args.description or 'None'}"""
        }
    
    # Process meeting request
    result = process_meeting_request(context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 