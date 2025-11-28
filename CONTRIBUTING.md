# Contributing to Hajri.ai

Thank you for your interest in contributing to Hajri.ai! 🎉

## 📋 Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Hajri.ai.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 💻 Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run the app
streamlit run app.py
```

## 📁 Project Structure

```
src/
├── config/         # Configuration
├── database/       # Database layer
├── core/           # Core business logic
├── services/       # Business services
├── ui/             # UI components
└── utils/          # Utilities
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8
- Use Black for formatting: `black .`
- Use isort for imports: `isort .`
- Maximum line length: 100 characters

### Type Hints
```python
def create_user(username: str, email: str) -> bool:
    """Create a new user."""
    pass
```

### Docstrings
```python
def calculate_attendance(student_id: int, subject_id: int) -> float:
    """
    Calculate attendance percentage for a student in a subject.
    
    Args:
        student_id: The student's user ID
        subject_id: The subject ID
        
    Returns:
        Attendance percentage (0-100)
        
    Raises:
        ValueError: If student or subject not found
    """
    pass
```

### Naming Conventions
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_database/test_connection.py
```

### Writing Tests
```python
def test_create_user():
    """Test user creation"""
    result = create_user("test_user", "test@example.com")
    assert result is True
```

## 🔄 Pull Request Process

1. **Update Documentation**: If you change functionality, update the docs
2. **Add Tests**: All new features must have tests
3. **Pass CI**: Ensure all tests and linting pass
4. **Update CHANGELOG**: Add your changes to CHANGELOG.md
5. **Request Review**: Tag maintainers for review

### PR Title Format
```
type(scope): description

Examples:
feat(auth): add password reset functionality
fix(database): resolve connection pooling issue
docs(readme): update installation instructions
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

## 🐛 Reporting Bugs

Use GitHub Issues with:
- Clear title
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, Python version)

## 💡 Suggesting Features

Open an issue with:
- Clear description
- Use case
- Proposed solution
- Alternatives considered

## 📞 Questions?

- Open a GitHub Discussion
- Check existing issues
- Read the documentation in `docs/`

---

Thank you for contributing! 🙏
