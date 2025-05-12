#!/usr/bin/env python3
"""
Meeting Workflow ADK - Streamlit Web Interface
Web interface for the meeting scheduling system
"""

import streamlit as st
import datetime
import json
from meeting_workflow_adk import process_meeting_request

# Page configuration
st.set_page_config(
    page_title="ADK Meeting Scheduling System",
    page_icon="📅",
    layout="wide"
)

# Page title
st.title("🤖 Google ADK Meeting Scheduling System")
st.markdown("Use multi-agent collaboration to schedule meetings, resolve conflicts, and send notifications")

# Sidebar - Introduction and instructions
with st.sidebar:
    st.header("👋 Welcome")
    st.markdown("""
    This system is built with Google ADK (Agent Development Kit) architecture,
    comprising multiple specialized agents collaborating to handle the meeting scheduling process:
    
    1. **Validator Agent** - Verifies attendee email formats
    2. **Scheduler Agent** - Handles Google Calendar integration and conflict resolution
    3. **Notifier Agent** - Generates and sends meeting notifications
    
    Please enter meeting information on the right to schedule.
    """)
    
    st.markdown("---")
    st.markdown("Powered by Google ADK and Gemini")

# Main form
with st.form("meeting_form"):
    st.subheader("Meeting Information")
    
    # Meeting subject
    summary = st.text_input("Meeting Subject", "Product Development Discussion")
    
    # Meeting date and time
    col1, col2 = st.columns(2)
    with col1:
        meeting_date = st.date_input("Meeting Date", datetime.datetime.now() + datetime.timedelta(days=1))
    with col2:
        meeting_time = st.time_input("Meeting Time", datetime.time(14, 0))
    
    # Combine date and time
    meeting_datetime = datetime.datetime.combine(meeting_date, meeting_time)
    
    # Meeting duration
    duration = st.slider("Duration (minutes)", 15, 180, 60, step=15)
    
    # Attendees
    attendees = st.text_area(
        "Attendee Emails (one per line)",
        "alice@example.com\nbob@example.com"
    )
    
    # Meeting description
    description = st.text_area("Meeting Description", "Discuss next quarter product development plans and progress tracking")
    
    # Submit button
    submit_button = st.form_submit_button("Schedule Meeting")

# Handle form submission
if submit_button:
    with st.spinner("Processing meeting scheduling..."):
        # Prepare attendee list
        attendee_list = [email.strip() for email in attendees.split("\n") if email.strip()]
        
        # Create query content
        query = f"""Schedule meeting:
        Subject: {summary}
        Time: {meeting_datetime.isoformat()}
        Duration: {duration} minutes
        Attendees: {', '.join(attendee_list)}
        Description: {description}
        """
        
        # Process request
        context = {"query": query}
        try:
            result = process_meeting_request(context)
            
            # Display results
            if result.get("status") == "success":
                st.success("✅ Meeting scheduled successfully!")
                st.json(result)
                
            elif result.get("status") == "conflict":
                st.warning("⚠️ Time conflicts detected")
                st.write(result.get("message", ""))
                
                # Show alternative time options
                if result.get("suggestions"):
                    st.subheader("Available Alternative Times")
                    for i, alt_time in enumerate(result.get("suggestions", [])):
                        dt = datetime.datetime.fromisoformat(alt_time)
                        st.write(f"{i+1}. {dt.strftime('%Y-%m-%d %H:%M')} ({dt.strftime('%A')})")
                    
                    st.info("Please select an alternative time and resubmit")
                
            else:
                st.error("❌ Scheduling failed")
                st.write(result.get("message", "Unknown error"))
                
        except Exception as e:
            st.error(f"Error during processing: {str(e)}")

# Show current process
st.markdown("---")
st.subheader("System Process")
col1, col2, col3 = st.columns(3)
with col1:
    st.info("Validator Agent ➡️ Check attendee data")
with col2:
    st.info("Scheduler Agent ➡️ Calendar API integration")
with col3:
    st.info("Notifier Agent ➡️ Prepare and send notifications") 