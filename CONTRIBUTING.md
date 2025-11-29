# Contributing to Orbit

## Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/steve-phan/orbit
cd orbit
```

2. **Create virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**
```bash
make install
```

## Code Quality Standards

### Formatting
We use **Black** for code formatting:
```bash
make format
```

### Linting
We use **Ruff** for linting:
```bash
make lint
```

### Type Checking
We use **MyPy** for static type checking:
```bash
mypy orbit/
```

### Running All Checks
```bash
make check
```

## Testing

### Run all tests
```bash
make test
```

### Run specific test
```bash
pytest tests/test_dag_executor.py::test_topological_sort_linear -v
```

### Test Coverage
```bash
pytest --cov=orbit tests/
```

## Architecture Guidelines

### 1. Separation of Concerns
- **API Layer** (`orbit/api`): HTTP endpoints, request/response handling
- **Service Layer** (`orbit/services`): Business logic
- **Repository Layer** (`orbit/repositories`): Data access
- **Models** (`orbit/models`): Database entities
- **Schemas** (`orbit/schemas`): Request/response validation

### 2. Dependency Injection
Use the dependency injection container in `orbit/core/dependencies.py`:

```python
from orbit.core.dependencies import get_workflow_service

@router.post("/workflows/")
async def create_workflow(
    service: WorkflowService = Depends(get_workflow_service)
):
    return await service.create_workflow(...)
```

### 3. Error Handling
Use custom exceptions from `orbit/core/exceptions.py`:

```python
from orbit.core.exceptions import WorkflowNotFoundError

raise WorkflowNotFoundError(
    "Workflow not found",
    details={"workflow_id": str(workflow_id)}
)
```

### 4. Logging
Use the logging infrastructure:

```python
from orbit.core.logging import get_logger

logger = get_logger("module_name")
logger.info("Operation completed")
logger.error("Operation failed", exc_info=True)
```

## Pull Request Process

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
- Write tests for new functionality
- Update documentation
- Follow code style guidelines

3. **Run quality checks**
```bash
make check
```

4. **Commit your changes**
```bash
git add .
git commit -m "feat: add new feature"
```

Use conventional commit messages:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

5. **Push and create PR**
```bash
git push origin feature/your-feature-name
```

## Code Review Checklist

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] No linting errors (`make lint`)
- [ ] Type hints are present
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No breaking changes (or documented)

## Project Structure

```
orbit/
├── api/              # API endpoints
│   └── v1/
│       ├── endpoints/
│       └── api.py
├── core/             # Core infrastructure
│   ├── config.py
│   ├── dependencies.py
│   ├── exceptions.py
│   └── logging.py
├── db/               # Database
│   └── session.py
├── models/           # Database models
│   └── workflow.py
├── repositories/     # Data access layer
│   └── workflow_repository.py
├── schemas/          # Pydantic schemas
│   └── workflow.py
└── services/         # Business logic
    ├── dag_executor.py
    ├── task_runner.py
    ├── websocket_manager.py
    └── workflow_service.py
```

## Adding New Features

### 1. New Endpoint
1. Create schema in `orbit/schemas/`
2. Add business logic to service in `orbit/services/`
3. Create endpoint in `orbit/api/v1/endpoints/`
4. Add tests in `tests/`

### 2. New Task Type
1. Add action type to `TaskRunner._execute_action()`
2. Implement execution logic
3. Add tests
4. Update documentation

## Questions?

Open an issue or reach out to the maintainers.
