# Multi-Agent Project Management System

A hierarchical multi-agent system for project management using Google's Agent Development Kit (ADK). This system showcases the use of specialized agents working together to manage tasks, dynamic load balancing, and agent coordination using the Agent-to-Agent (A2A) protocol.

## Architecture

This project implements a multi-agent system with three types of agents organized in a hierarchical structure:

1. **Manager Agent** - Responsible for task assignment, project oversight, and decision-making
2. **Engineer Agents** - Responsible for implementing tasks and reporting progress
3. **Tester Agents** - Responsible for testing completed tasks and reporting results

The system features:
- Dynamic load balancing to distribute tasks optimally across agents
- Natural language understanding with Google Gemini integration
- Clear responsibility attribution through task assignment and status tracking
- Agent-to-agent coordination via a workflow coordinator
- Adherence to A2A protocol standards with `.well-known/agent.json` manifests
- REST API endpoints for each agent type

## A2A Protocol Implementation

Each agent in this system follows the Agent-to-Agent (A2A) protocol, which is a standard in Google's ADK:

- Each agent has a `.well-known/agent.json` manifest file that defines:
  - Agent capabilities
  - API endpoints
  - Request/response schemas
  - Authentication methods

- The agent manifest serves as a contract between agents, allowing:
  - Standard discovery of capabilities
  - Consistent API interfaces
  - Easy integration with other ADK agents

## Natural Language Understanding with Gemini

The system integrates Google's Gemini AI to enable natural language understanding for all agents:

- Each agent can process and understand natural language commands
- Commands are automatically routed to the appropriate agent type
- The system intelligently extracts parameters from natural language input
- Fallback mechanisms ensure commands work even without Gemini API access

### Setting Up Gemini

To enable Gemini AI features:

1. Obtain a Google Gemini API key from [Google AI Studio](https://ai.google.dev/)
2. Create a `.env` file in the project root and add your API key:

```
GEMINI_API_KEY=your_api_key_here
```

3. Run the system as usual:

```bash
python -m multi_agent_pm
```

The system will automatically load your API key from the .env file.

### Natural Language Command Examples

With Gemini enabled, you can use more natural language commands like:

- "Create a new high-priority task called 'Implement payment gateway' to add Stripe integration"
- "What's the status of TASK-12345678?"
- "I need to know all current tasks assigned to engineers"
- "Can you show me all failed tests in the project?"
- "Reassign the authentication task to Engineer2 because they have more experience"

The system will interpret these commands, extract the relevant parameters, and route them to the appropriate agent.

## Project Structure

```
multi_agent_pm/
├── __init__.py
├── __main__.py         # Entry point for running as a module
├── ai/                 # Natural language processing with Gemini
│   ├── __init__.py
│   ├── agent_nlp_handler.py
│   └── gemini_client.py
├── agents/             # Agent implementations
│   ├── __init__.py
│   ├── engineer/       # Engineer agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── .well-known/
│   │       └── agent.json
│   ├── manager/        # Manager agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── .well-known/
│   │       └── agent.json
│   └── tester/         # Tester agent
│       ├── __init__.py
│       ├── agent.py
│       └── .well-known/
│           └── agent.json
├── common.py           # Shared data models and utilities
├── main.py             # Main system implementation
└── workflow/           # Workflow coordination
    ├── __init__.py
    └── coordinator.py
```

## Installation

1. Ensure you have Python 3.8+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the System

To run the multi-agent system:

```bash
python -m multi_agent_pm
```

This will:
1. Initialize the workflow coordinator
2. Set up all agents with appropriate capacities
3. Preload sample tasks for demonstration
4. Start the API servers for each agent
5. Start the agent interaction loop
6. Start background workload balancing

### Interacting with the System

When running, you can interact with the agents using plain text commands. Here are some examples for each agent type:

#### Manager Commands

- `create task "Task title" "Task description" high feature` - Create a new task
- `assign task TASK-12345678` - Assign a task to an agent
- `list tasks` - List all tasks in the system
- `review task TASK-12345678` - Review a completed or tested task
- `agent status` - Get status report on all agents

#### Engineer Commands

- `my tasks` - List tasks assigned to this engineer
- `work on TASK-12345678` - Start working on a specific task
- `complete task TASK-12345678` - Mark a task as completed
- `status` - Get status information for this engineer

#### Tester Commands

- `completed tasks` - List all tasks ready for testing
- `test task TASK-12345678` - Pick up a task for testing
- `my tasks` - List tasks assigned to this tester
- `submit test results TASK-12345678` - Submit test results (add "fail" to fail)
- `status` - Get status information for this tester

### REST API Endpoints

Each agent exposes REST API endpoints as defined in their `.well-known/agent.json` files. The servers run on different ports:

- Manager API: http://127.0.0.1:8001
- Engineer APIs: http://127.0.0.1:8010, 8011, 8012
- Tester APIs: http://127.0.0.1:8020, 8021

#### Manager API Endpoints

- POST `/api/agents/manager/create_task` - Create a new task
- POST `/api/agents/manager/assign_task` - Assign a task to an agent
- POST `/api/agents/manager/list_tasks` - List all tasks with optional filtering
- POST `/api/agents/manager/review_task` - Review a completed or tested task
- POST `/api/agents/manager/get_agent_status` - Get status of all agents

#### Engineer API Endpoints

- POST `/api/agents/engineer/list_my_tasks` - List tasks assigned to this engineer
- POST `/api/agents/engineer/work_on_task` - Start working on a task
- POST `/api/agents/engineer/complete_task` - Mark a task as completed
- POST `/api/agents/engineer/get_status` - Get engineer status

#### Tester API Endpoints

- POST `/api/agents/tester/list_completed_tasks` - List tasks ready for testing
- POST `/api/agents/tester/list_my_tasks` - List tasks assigned to this tester
- POST `/api/agents/tester/test_task` - Pick up a task for testing
- POST `/api/agents/tester/submit_test_results` - Submit test results
- POST `/api/agents/tester/get_status` - Get tester status

### API Example (using curl)

Create a task:
```bash
curl -X POST http://127.0.0.1:8001/api/agents/manager/create_task \
  -H "Content-Type: application/json" \
  -d '{"title": "Test API Task", "description": "Testing the API workflow", "priority": "high", "task_type": "feature"}'
```

Assign a task:
```bash
curl -X POST http://127.0.0.1:8001/api/agents/manager/assign_task \
  -H "Content-Type: application/json" \
  -d '{"task_id": "TASK-12345678", "agent_id": "Engineer1"}'
```

## System Features

### Dynamic Load Balancing

The system performs automatic workload balancing every 60 seconds (configurable). This:
1. Identifies overloaded agents (>80% capacity)
2. Identifies underloaded agents (<50% capacity)
3. Redistributes tasks to balance workload

### Task Workflow

Tasks follow a defined workflow:
1. Creation (Manager)
2. Assignment (Manager → Engineer)
3. Implementation (Engineer)
4. Completion (Engineer)
5. Testing (Tester)
6. Approval/Rejection (Manager)

### Natural Language Processing

The system uses Google Gemini to process commands by:
1. Determining which agent type should handle the command
2. Using Gemini to convert natural language to a structured API operation
3. Extracting parameters from the command text
4. Calling the appropriate agent API with the extracted parameters
5. Providing fallback command parsing when Gemini is unavailable

## Architecture Details

### Agent Hierarchy

The system uses ADK's agent hierarchy with A2A protocol:
- SequentialAgent (Root Workflow Agent)
  - Manager Agent (with A2A manifest)
  - Engineer Agents (with A2A manifest)
  - Tester Agents (with A2A manifest)

### Shared State

All agents share access to:
- Task store - Repository of all tasks in the system
- Agent loads - Current workload information for each agent

## Customization

### Agent Capacities

You can customize agent capacities through environment variables:
- `MANAGER_MAX_CAPACITY` - Maximum tasks for the manager agent (default: 10)
- `ENGINEER_MAX_CAPACITY` - Maximum tasks for engineer agents (default: 5)
- `TESTER_MAX_CAPACITY` - Maximum tasks for tester agents (default: 3)

### Development

#### Adding New Agent Types

To add a new agent type:
1. Create a new subdirectory in `multi_agent_pm/agents/`
2. Create a `.well-known/agent.json` manifest file defining capabilities
3. Implement the agent class extending `BaseAgent` with matching API
4. Update the `WorkflowCoordinator` to include the new agent type

#### Extending Functionality

To add new capabilities to an agent:
1. Update the `.well-known/agent.json` manifest with new capabilities
2. Add corresponding API methods to the agent class
3. Update any necessary data models in `common.py`

## License

This project is licensed under the MIT License.
