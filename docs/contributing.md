# Contributing

Thank you for your interest in contributing to SnowMapPy!

---

## Ways to Contribute

We welcome contributions of all kinds:

- :bug: **Bug Reports** - Found a problem? Let us know!
- :bulb: **Feature Requests** - Have an idea? We'd love to hear it!
- :memo: **Documentation** - Help improve our docs
- :computer: **Code** - Fix bugs or implement features
- :test_tube: **Testing** - Help test new features

---

## Getting Started

### 1. Fork the Repository

Click the "Fork" button on [GitHub](https://github.com/haytamelyo/SnowMapPy).

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/SnowMapPy.git
cd SnowMapPy
```

### 3. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 4. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

---

## Development Workflow

### Code Style

We use the following tools for code quality:

- **Black** for formatting
- **isort** for import sorting
- **mypy** for type checking

Format your code:

```bash
# Format code
black SnowMapPy/
isort SnowMapPy/

# Type check
mypy SnowMapPy/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=SnowMapPy

# Run specific test file
pytest tests/test_processor.py
```

### Building Documentation

```bash
# Install docs dependencies
pip install -r requirements-docs.txt

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

---

## Making Changes

### Code Changes

1. Make your changes
2. Add/update tests
3. Update documentation if needed
4. Run tests and linting
5. Commit with clear message

### Commit Messages

Follow conventional commits:

```
feat: add cubic interpolation method
fix: handle edge case in DEM loading
docs: update installation instructions
test: add tests for spatial correction
refactor: simplify memory tracking
```

### Pull Requests

1. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub

3. Fill out the PR template:
   - Description of changes
   - Related issues
   - Testing performed

4. Wait for review

---

## Project Structure

```
SnowMapPy/
├── SnowMapPy/           # Main package
│   ├── __init__.py      # Package exports
│   ├── cli.py           # CLI commands
│   ├── _numba_kernels.py # JIT-compiled functions
│   ├── cloud/           # GEE integration
│   │   ├── auth.py      # Authentication
│   │   ├── loader.py    # Data loading
│   │   └── processor.py # Processing pipeline
│   └── core/            # Utilities
│       ├── spatial.py   # Spatial operations
│       ├── temporal.py  # Temporal processing
│       └── data_io.py   # I/O functions
├── docs/                # Documentation
├── tests/               # Test suite
├── pyproject.toml       # Package config
└── README.md            # Main readme
```

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior

- Be respectful and constructive
- Welcome newcomers
- Focus on the issue, not the person
- Accept feedback graciously

### Unacceptable Behavior

- Harassment or discrimination
- Personal attacks
- Trolling or spam

---

## Questions?

- :material-github: Open a [Discussion](https://github.com/haytamelyo/SnowMapPy/discussions)
- :material-email: Email the maintainers

---

## Recognition

Contributors are recognized in:

- Release notes
- Contributors list
- Social media announcements

Thank you for helping make SnowMapPy better! :heart:
