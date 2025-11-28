# 🚀 Quick Start Guide

## ⚡ Fastest Way (One Command!)

```bash
# Using uv (recommended)
uv run streamlit run app.py
```

**That's it!** The app auto-installs dependencies and runs.

---

## 🐳 Docker (One Command!)

```bash
docker-compose up
```

Access at: `http://localhost:8501`

---

## 📦 Using Makefile

```bash
# Run with uv
make run

# Run with Docker
make docker-run

# Setup and run
make all

# See all commands
make help
```

---

## 🔧 Traditional Setup

```bash
# 1. Clone
git clone https://github.com/krishujeniya/Hajri.ai.git
cd Hajri.ai

# 2. Environment
cp .env.example .env
# Edit .env with your credentials

# 3. Install
pip install -r requirements.txt

# 4. Setup database
python3 scripts/setup_db.py

# 5. Run
streamlit run app.py
```

---

## 🎯 First Login

- **URL**: `http://localhost:8501`
- **Username**: `admin` (or from `.env`)
- **Password**: From `.env` file

---

## 📚 Next Steps

1. Register students (capture 10 photos)
2. Create subjects
3. Assign teachers
4. Take attendance!

See [README.md](../README.md) for full documentation.
