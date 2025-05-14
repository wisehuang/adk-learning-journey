# Google ADK Meeting Scheduling Multi-Agent System

A multi-agent meeting scheduling system implemented using Google Agent Development Kit (ADK), automatically handling meeting scheduling, conflict resolution, and attendee notifications through Google Calendar API.

## System Architecture

This project adopts Google ADK's multi-agent architecture, dividing meeting scheduling into multiple specialized agents working together:

- **Validator Agent**: Responsible for validating attendee email formats
- **Scheduler Agent**: Handles Google Calendar integration and conflict resolution
- **Notifier Agent**: Generates and sends meeting notifications to participants

These agents collaborate through ADK's SequentialAgent to form a complete workflow.

## Features

- 📅 Google Calendar API integration
- 🔍 Intelligent conflict detection and resolution
- 🔄 Automatic alternative time suggestions
- ✉️ Automated notifications to all meeting participants
- 🤖 Gemini-based multi-agent collaboration

## Installation and Configuration

### Requirements

- Python 3.8+
- [Google Cloud Project](https://console.cloud.google.com/) with Calendar API enabled
- Google ADK authorization

### Installation Steps

1. Clone this repository:
```bash
git clone <repository-url>
cd meeting_workflow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Google Cloud Setup:
   - Create a project and enable Calendar API
   - Configure OAuth consent screen
   - Create OAuth client credentials (Desktop application)
   - Download `credentials.json` to the project root directory

## Usage

### Command Line Usage

```bash
python meeting_workflow_adk.py --summary "Product Meeting" --time "2023-08-01T14:00:00" --duration 60 --attendees "alice@example.com,bob@example.com" --description "Product development meeting"
```

Or run for a demonstration with example parameters:

```bash
python meeting_workflow_adk.py
```

### Web Interface

Launch the Streamlit web interface:

```bash
streamlit run streamlit_app.py
```

Then open the displayed URL in your browser (typically http://localhost:8501)

## Project Structure

```
meeting_workflow/
├── meeting_workflow_adk.py  # Main ADK implementation
├── streamlit_app.py         # Web interface
├── common/                  # Shared utilities
│   └── google_auth.py       # Google authentication functionality
├── requirements.txt         # Dependencies
└── README.md                # Project documentation
```

## ADK Agent Design

This project uses Google ADK's multi-agent collaboration features, designed as follows:

```python
# Validator agent
validate_agent = Agent(
    name="attendee_validator",
    model="gemini-2.5-pro-preview-05-06",
    tools=[ValidateAttendeesTool()],
    instruction="Validate meeting participant email formats"
)

# Scheduler agent
scheduling_agent = Agent(
    name="meeting_scheduler", 
    model="gemini-2.5-pro-preview-05-06",
    tools=[ScheduleMeetingTool()],
    instruction="Handle meeting scheduling and conflict resolution"
)

# Notifier agent
notification_agent = Agent(
    name="notification_sender",
    model="gemini-2.5-pro-preview-05-06",
    instruction="Generate meeting notification content and send"
)

# Main workflow
meeting_workflow = SequentialAgent(
    name="meeting_workflow",
    sub_agents=[validate_agent, scheduling_agent, notification_agent],
    instruction="Complete meeting scheduling workflow"
)
```

## Error Handling

The system has comprehensive error handling mechanisms, including:

- Email format validation errors
- Google Calendar API errors
- Meeting time conflicts
- Network connection issues

## Extensible Features

The project can be further extended:

- Cross-timezone support
- Meeting room reservation integration
- More calendar synchronization options
- Natural language input (e.g.: "Schedule a one-hour product meeting next Monday afternoon")

## License

MIT License 