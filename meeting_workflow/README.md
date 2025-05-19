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
- 🐳 Containerized deployment with Docker
- 🔐 Secure credential management with Google Cloud Secret Manager

## Installation and Configuration

### Requirements

- Python 3.12+
- [Google Cloud Project](https://console.cloud.google.com/) with:
  - Calendar API enabled
  - Cloud Run API enabled
  - Secret Manager API enabled
  - Container Registry API enabled
- Google ADK authorization

### Local Development Setup

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
   - Create a project and enable required APIs
   - Configure OAuth consent screen
   - Create OAuth client credentials (Desktop application)
   - Download `credentials.json` to the project root directory

### Container Deployment

1. Build and test the container locally:
```bash
# Build the container
docker build -t meeting-scheduler .

# Run the container locally
docker run -p 8080:8080 meeting-scheduler
```

2. Deploy to Google Cloud Run:
```bash
gcloud run deploy meeting-workflow \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

3. Set up Google Cloud Secret Manager:
```bash
# Create secrets
gcloud secrets create calendar-credentials --replication-policy="automatic"
gcloud secrets create calendar-token --replication-policy="automatic"

# Add credentials
gcloud secrets versions add calendar-credentials --data-file="credentials.json"
```

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

### Cloud Run Deployment

After deployment, access the application at the URL provided by Cloud Run.

## Project Structure

```
meeting_workflow/
├── meeting_workflow_adk.py  # Main ADK implementation
├── streamlit_app.py         # Web interface
├── Dockerfile              # Container configuration
├── .dockerignore          # Docker build exclusions
├── common/                 # Shared utilities
│   └── google_auth.py      # Google authentication functionality
├── requirements.txt        # Dependencies
└── README.md              # Project documentation
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

## Security Considerations

- Credentials and tokens are stored in Google Cloud Secret Manager
- Container runs with minimal permissions
- Environment variables are used for configuration
- Sensitive files are excluded from container builds

## Error Handling

The system has comprehensive error handling mechanisms, including:

- Email format validation errors
- Google Calendar API errors
- Meeting time conflicts
- Network connection issues
- Container deployment errors
- Secret Manager access errors

## Extensible Features

The project can be further extended:

- Cross-timezone support
- Meeting room reservation integration
- More calendar synchronization options
- Natural language input (e.g.: "Schedule a one-hour product meeting next Monday afternoon")
- Additional Cloud Run configurations
- Custom domain mapping
- SSL/TLS configuration

## License

MIT License 