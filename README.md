# Orbit: Distributed Task Orchestration System

Orbit is a high-performance, asynchronous distributed task orchestration system designed to manage complex workflows with reliability and scalability. Built on modern architectural patterns, it leverages the power of FastAPI and AsyncIO to handle high-throughput task execution.

## Key Features

1.  **Workflow Management**: Define complex Directed Acyclic Graphs (DAGs) of tasks.
2.  **Real-time Monitoring**: WebSocket-based updates for task progress.
3.  **Distributed Execution Model**: Architecture designed for scalable worker nodes.
4.  **Robust Security**: JWT Authentication and OAuth2 scopes.
5.  **High Performance**: Fully async database access and request handling.

## Tech Stack

*   **Framework**: FastAPI
*   **Database**: PostgreSQL (Async via SQLModel/SQLAlchemy)
*   **Validation**: Pydantic V2
*   **Task Queue**: Redis & Celery
*   **Containerization**: Docker

## Getting Started

1.  Create a virtual environment: `python3 -m venv .venv`
2.  Activate it: `source .venv/bin/activate`
3.  Install dependencies: `pip install -e .`
4.  Run the server: `uvicorn orbit.main:app --reload`
