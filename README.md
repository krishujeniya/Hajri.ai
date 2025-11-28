# 🎓 Hajri.ai - AI-Powered Attendance System

<div align="center">

![GitHub repo size](https://img.shields.io/github/repo-size/krishujeniya/Hajri.ai)
![GitHub contributors](https://img.shields.io/github/contributors/krishujeniya/Hajri.ai)
![GitHub stars](https://img.shields.io/github/stars/krishujeniya/Hajri.ai?style=social)
![GitHub forks](https://img.shields.io/github/forks/krishujeniya/Hajri.ai?style=social)

**An intelligent, automated attendance management system using facial recognition and liveness detection.**

[Features](#-features) • [Quick Start](#-quick-start) • [Docker](#-docker-deployment) • [Documentation](#-documentation)

</div>

---

## 🚀 Quick Start

### **One-Command Setup** (Recommended)

```bash
# Using uv (fastest)
uv run streamlit run src/app.py
```

That's it! The app will automatically:
- ✅ Install all dependencies
- ✅ Initialize the database
- ✅ Start the application

### **Traditional Setup**

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/Hajri.ai.git
cd Hajri.ai

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python3 scripts/setup_db.py

# 5. Run application
streamlit run src/app.py
```

---

## 🐳 Docker Deployment

### **One-Command Docker Run**

```bash
docker-compose up
```

The application will be available at `http://localhost:8501`

### **Manual Docker Build**

```bash
# Build image
docker build -t hajri-ai .

# Run container
docker run -p 8501:8501 hajri-ai
```

---

## ✨ Features

### **🔐 Role-Based Access Control**
- **Admin Portal**: Full system management
- **Teacher Portal**: Attendance tracking and reporting
- **Student Portal**: View personal attendance records

### **🤖 AI-Powered Recognition**
- ⚡ Fast facial recognition using DeepFace
- 🔒 Anti-spoofing with liveness detection
- 📸 Mark entire class from single photo
- 🎯 High accuracy with SFace model

### **📊 Comprehensive Analytics**
- Real-time attendance dashboards
- Lecture-wise trends and statistics
- Automatic defaulter identification
- Export reports (CSV & PDF)

### **📧 Smart Notifications**
- Automated email alerts for low attendance
- Bulk notification system
- Customizable thresholds

### **🎨 Modern UI**
- Glassmorphism dark theme
- Responsive design
- Intuitive user experience

---

## 📁 Project Structure

```
hajri.ai/
├── assets/              # Project assets (logo, database, training images)
├── src/                 # Source code
│   ├── app.py          # Main application entry point
│   ├── config/         # Configuration management
│   ├── database/       # Database operations
│   ├── services/       # Business services
│   ├── ui/             # UI components & styles
│   ├── legacy/         # Legacy modules (to be refactored)
│   └── models/         # AI model files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── tests/              # Test files
├── run.py              # Quick launcher
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose configuration
└── Makefile            # Build automation
```

---

## 🛠️ Technology Stack

- **Framework**: Streamlit
- **AI/ML**: DeepFace, OpenCV
- **Database**: SQLite
- **Authentication**: Streamlit-Authenticator
- **Image Processing**: Albumentations, Pillow
- **Reports**: FPDF2, Pandas

---

## 📖 Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in 5 minutes
- **[Contributing Guide](docs/CONTRIBUTING.md)** - How to contribute
- **[Architecture](docs/FINAL_STRUCTURE.md)** - Project structure details

---

## ⚙️ Configuration

### **Environment Variables**

Create a `.env` file in the root directory:

```env
# Application
SECRET_KEY=your_random_secret_key_here

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password

# Email Configuration (for notifications)
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-digit-app-password
```

### **Gmail App Password Setup**

For email notifications, use a Gmail App Password:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Generate App Password for "Mail"
4. Use the 16-digit password in `.env`

---

## 🎯 Usage

### **First-Time Setup**

1. **Login as Admin**
   - Username: `admin` (or from `.env`)
   - Password: From `.env` file

2. **Register Students**
   - Navigate to "Register User" tab
   - Select "student" role
   - Capture 10 photos for training
   - AI model trains automatically

3. **Create Subjects**
   - Go to "Manage" tab
   - Create subjects
   - Assign teachers
   - Enroll students

4. **Take Attendance**
   - Select subject
   - Create/select lecture
   - Upload class photo or use camera
   - Review and save attendance

### **For Teachers**

- Mark attendance via photo upload or live camera
- View attendance dashboards and trends
- Download reports (CSV/PDF)
- Send email notifications to defaulters

### **For Students**

- View attendance percentage for all subjects
- Check detailed lecture-wise attendance
- Track attendance trends

---

## 🔧 Utility Scripts

```bash
# Initialize database
python3 scripts/setup_db.py

# Create backup
python3 scripts/backup_data.py

# Clean up old files
python3 scripts/cleanup_old_files.py
```

---

## 🐳 Docker Commands

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache
```

---

## 📦 Using Makefile

```bash
# Install dependencies
make install

# Run application
make run

# Run with Docker
make docker-run

# Run tests
make test

# Clean build artifacts
make clean

# Format code
make format

# Show all commands
make help
```

---

## 🧪 Development

### **Setup Development Environment**

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Format code
black .
isort .

# Run tests
pytest

# Type checking
mypy src/
```

### **Project Guidelines**

- Follow PEP 8 style guide
- Add docstrings to all functions
- Write tests for new features
- Update documentation

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

### **Quick Contribution Steps**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with these amazing open-source libraries:
- [Streamlit](https://streamlit.io/)
- [DeepFace](https://github.com/serengil/deepface)
- [OpenCV](https://opencv.org/)
- [Pandas](https://pandas.pydata.org/)

---

## 📞 Support

- 🐛 Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/Hajri.ai/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/Hajri.ai/discussions)
- 📖 Documentation: See `docs/` folder

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

<div align="center">

**Made with ❤️ by the Hajri.ai Team**

[⬆ Back to Top](#-hajriai---ai-powered-attendance-system)

</div>
