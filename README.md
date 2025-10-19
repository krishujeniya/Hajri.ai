
# 🤖 Hajri.ai - Smart Attendance System

[![Status](https://img.shields.io/badge/Status-Active-brightgreen)](https://github.com/) [![License](https://img.shields.io/badge/License-MIT-blue)](./LICENSE)

Hajri.ai is a modern, web-based smart attendance system designed to automate the process of marking attendance using real-time facial recognition. Built with Python, Streamlit, and OpenCV, it provides an intuitive interface for managing students, tracking attendance, and generating reports, all packaged within a convenient Docker container for easy deployment.

<br>

![Hajri.ai Screenshot](https://i.imgur.com/your-screenshot-link.png) 
*--(Note: Replace this with a real screenshot of your running application!)--*

---

## ✨ Key Features

-   **Real-Time Video Attendance**: Mark attendance automatically through a live webcam feed.
-   **Multiple Attendance Modes**: Flexible options to take attendance via live video, single photo capture, or by uploading a class picture.
-   **Comprehensive Dashboard**: Visualize attendance data with metrics, lecture trends, and a defaulter list.
-   **Automated Email Alerts**: Automatically send warning emails to students with low attendance.
-   **Bulk Student Registration**: Register multiple students at once by uploading a simple CSV file.
-   **Full Data Management**: Easily add/remove students from subjects, delete lecture records, and permanently remove student data.
-   **Dockerized Deployment**: Run the entire application with a single command using Docker Compose, ensuring a consistent and hassle-free setup.

---

## 🛠️ Technology Stack

| Technology | Description |
| :--- | :--- |
| **Python** | Core programming language. |
| **Streamlit** | For creating the interactive web application interface. |
| **OpenCV** | Used for all computer vision tasks, including face detection and recognition (LBPH). |
| **Pandas** | For efficient data manipulation and management of student and attendance records. |
| **Pillow** | For image processing and drawing bounding boxes. |
| **Docker** | For containerizing the application, making it portable and easy to deploy. |

---

## 🚀 Getting Started

Follow these instructions to get Hajri.ai running on your local machine using Docker.

### Prerequisites

You must have the following installed on your system:
-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/hajri-ai.git](https://github.com/your-username/hajri-ai.git)
    cd hajri-ai
    ```

2.  **Configure Email Credentials (Optional)**
    If you want to use the email notification feature, you need to provide your Gmail credentials securely.

    -   Create a directory named `.streamlit`:
        ```bash
        mkdir .streamlit
        ```
    -   Inside it, create a file named `secrets.toml`:
        ```bash
        nano .streamlit/secrets.toml
        ```
    -   Add your credentials in the following format. **Use a Google App Password, not your regular password.**
        ```toml
        # .streamlit/secrets.toml
        SENDER_EMAIL = "your_email@gmail.com"
        SENDER_PASSWORD = "your_16_digit_app_password"
        ```
    -   Save and exit the file (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

3.  **Build and Run with Docker Compose**
    From the root directory of the project, run the following command:
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker image based on the `Dockerfile` and start the application. The `--build` flag is only needed the first time or after making changes to the configuration.

4.  **Access the Application**
    Open your web browser and navigate to:
    **`http://localhost:8501`**

    Your Hajri.ai application is now live!

---

## 📖 How to Use

1.  **Register Students**:
    -   Navigate to the **"🧑‍🎓 Register Student"** tab.
    -   Either use the **Bulk Upload** feature with a CSV file or enroll students one by one using the **Individual Enrollment** form.
    -   For individual enrollment, the app will guide you to capture 50 images of the student's face.
    -   The model will automatically train after image capture is complete.

2.  **Take Attendance**:
    -   Go to the **"📸 Take Attendance"** tab.
    -   Configure the session by selecting a **Subject** and a **Lecture**.
    -   Choose your preferred mode: **Live Video**, **Upload Image**, or **Capture Photo**.
    -   For Live Video, click "Start Session" to activate the camera.
    -   After students are recognized, click "Confirm and Save Attendance".

3.  **Monitor & Report**:
    -   Visit the **"📊 Dashboard"** tab to view overall statistics, trends, and defaulter lists.
    -   Download a full attendance report as a CSV file.

4.  **Manage Data**:
    -   Use the **"⚙️ Manage"** tab to add/remove students from subjects, delete lecture records, or permanently erase a student's data from the system.

---

## 📂 Project Structure

````

.
├── .streamlit/
│   └── secrets.toml        \# Secure credentials for email
├── Attendance/             \# Stores attendance CSV files
├── StudentDetails/         \# Stores the main student details CSV
├── TrainingImage/          \# Stores captured images of students for training
├── TrainingImageLabel/     \# Stores the trained model (Trainner.yml)
├── app.py                  \# The main Streamlit application file (UI)
├── docker-compose.yml      \# Defines the Docker service and volumes
├── Dockerfile              \# Blueprint for building the Docker image
├── hajri\_utils.py          \# Backend logic for face recognition, data handling, etc.
├── haarcascade\_frontalface\_default.xml \# OpenCV model for face detection
├── requirements.txt        \# Python package dependencies
└── README.md               \# This file

```

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

## 👨‍💻 Author

- **Your Name**
- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: [Your LinkedIn Profile](https://www.linkedin.com/in/your-profile/)

