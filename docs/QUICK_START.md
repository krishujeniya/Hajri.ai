# 🚀 Quick Start Guide

## ⚡ One Command (Fastest!)

```bash
uv run streamlit run src/app.py
```

**That's it!** Auto-installs everything and runs.

---

## 🐳 Docker (One Command!)

```bash
docker-compose up
```

Access at: `http://localhost:8501`

---

## 📦 Using Makefile

```bash
make run          # Run with uv
make docker-run   # Run with Docker
make help         # See all commands
```

---

## 🔧 Traditional Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/Hajri.ai.git
cd Hajri.ai

# 2. Environment
cp .env.example .env
# Edit .env with your credentials

# 3. Install
pip install -r requirements.txt

# 4. Setup database
python3 scripts/setup_db.py

# 5. Run
streamlit run src/app.py
```

---

## 🎯 First Login

- **URL**: `http://localhost:8501`
- **Username**: From `.env` (default: `admin`)
- **Password**: From `.env` file

---

## 📚 Next Steps

1. Register students (capture 10 photos)
2. Create subjects
3. Assign teachers
4. Take attendance!

See [README.md](../README.md) for full documentation.
