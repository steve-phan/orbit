# Orbit - Distributed Task Orchestration System

A high-performance, production-ready distributed task orchestration system built with modern Python. Orbit manages complex workflows through Directed Acyclic Graphs (DAGs), providing real-time monitoring and scalable execution.

## 🎯 Core Features

### Workflow Orchestration
- **DAG-based Task Management**: Define complex task dependencies using Directed Acyclic Graphs
- **Topological Sorting**: Intelligent task ordering with automatic parallelization
- **Circular Dependency Detection**: Built-in validation prevents invalid workflow configurations

### Real-time Monitoring
- **WebSocket Integration**: Live updates for workflow and task status changes
- **Interactive Dashboard**: Web-based UI for monitoring and controlling workflows
- **Event Streaming**: Real-time broadcast of execution events to all connected clients

### High Performance
- **Fully Async Architecture**: Built on FastAPI and AsyncIO for maximum throughput
- **Parallel Task Execution**: Concurrent execution of independent tasks
- **Non-blocking I/O**: Async database operations using SQLModel and AsyncPG

### Production Ready
- **Comprehensive Testing**: Unit tests with pytest and pytest-asyncio
- **Type Safety**: Full Pydantic v2 validation and type hints
- **Database Migrations**: Alembic support for schema versioning
- **Docker Support**: Containerized deployment with docker-compose

## 🏗️ Architecture

```
orbit/
├── api/              # FastAPI routes and endpoints
│   └── v1/
│       ├── endpoints/
│       │   ├── workflows.py    # Workflow CRUD and execution
│       │   └── websocket.py    # Real-time WebSocket updates
│       └── api.py              # API router configuration
├── core/             # Core configuration
│   └── config.py               # Application settings
├── db/               # Database layer
│   └── session.py              # Async session management
├── models/           # SQLModel database models
│   └── workflow.py             # Workflow and Task models
├── schemas/          # Pydantic schemas
│   └── workflow.py             # Request/response schemas
└── services/         # Business logic
    ├── dag_executor.py         # Topological sort algorithm
    ├── task_runner.py          # Task execution engine
    └── websocket_manager.py    # WebSocket connection manager
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL (optional, defaults to SQLite for development)

### Installation

1. **Clone and setup environment**:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. **Start the API server**:
```bash
uvicorn orbit.main:app --reload
```

3. **Access the dashboard**:
Open `dashboard.html` in your browser or visit `http://localhost:8000/docs` for the interactive API documentation.

## 📖 Usage

### Creating a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflows/ \
-H "Content-Type: application/json" \
-d '{
  "name": "Data Pipeline",
  "description": "ETL workflow with parallel processing",
  "tasks": [
    {
      "name": "extract",
      "action_type": "http_request",
      "action_payload": {"url": "https://api.example.com/data"},
      "dependencies": []
    },
    {
      "name": "transform",
      "action_type": "python_script",
      "action_payload": {"script": "transform.py"},
      "dependencies": ["extract"]
    },
    {
      "name": "load",
      "action_type": "shell_command",
      "action_payload": {"command": "load_data.sh"},
      "dependencies": ["transform"]
    }
  ]
}'
```

### Executing a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflows/{workflow_id}/execute
```

### Monitoring via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Task update:', update);
};
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

The test suite includes:
- Topological sort algorithm validation
- Circular dependency detection
- Complex DAG execution scenarios
- Edge case handling

## 🐳 Docker Deployment

Start PostgreSQL and Redis:

```bash
docker-compose up -d
```

Update `.env` file:
```
DATABASE_URL=postgresql+asyncpg://orbit:orbit_password@localhost:5432/orbit_db
```

## 📊 Supported Task Types

- `http_request`: Execute HTTP API calls
- `python_script`: Run Python scripts
- `shell_command`: Execute shell commands
- `sleep`: Delay execution (for testing)

## 🔒 Security

- JWT authentication support (configurable)
- OAuth2 scopes for authorization
- CORS middleware for cross-origin requests
- Environment-based secret management

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL (production) / SQLite (development)
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Validation**: Pydantic V2
- **Testing**: pytest, pytest-asyncio
- **Containerization**: Docker & Docker Compose

## 📈 Performance

- Fully asynchronous request handling
- Connection pooling for database operations
- Efficient task scheduling with topological sort
- Parallel execution of independent tasks

## 🤝 Contributing

This is a production system. Contributions should include:
- Comprehensive tests
- Type hints
- Documentation updates
- Performance considerations

## 📝 License

MIT License - See LICENSE file for details

## 🔗 API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
