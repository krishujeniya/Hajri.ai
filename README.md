<a id="readme-top"></a>

![GitHub repo size](https://img.shields.io/github/repo-size/krishujeniya/Hajri.ai)
![GitHub contributors](https://img.shields.io/github/contributors/krishujeniya/Hajri.ai)
![GitHub stars](https://img.shields.io/github/stars/krishujeniya/Hajri.ai?style=social)
![GitHub forks](https://img.shields.io/github/forks/krishujeniya/Hajri.ai?style=social)

<br />
<div align="center">
  <a href="https://github.com/krishujeniya/Hajri.ai"><img src="logo.png" alt="Logo" width="80" height="80"></a>

<h1 align="center">Hajri.ai</h1>

  <p align="center">
    An AI-powered, automated attendance system using facial recognition.
    <br />
    <a href="https://github.com/krishujeniya/Hajri.ai">View Demo (Not Live)</a>
    ·
    <a href="https://github.com/krishujeniya/Hajri.ai/issues">Report Bug</a>
    ·
    <a href="https://github.com/krishujeniya/Hajri.ai/issues">Request Feature</a>
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#key-features">Key Features</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## 🚀 About The Project

**Hajri.ai** is an intelligent attendance management system designed for modern educational institutions. It replaces traditional manual attendance with a fast, accurate, and spoof-proof solution built on facial recognition.

The system features distinct, secure portals for Administrators, Teachers, and Students, each with tools tailored to their needs. From a single uploaded class photo or a live camera feed, Hajri.ai can detect and recognize all registered students, perform liveness checks to prevent spoofing, and automatically update attendance records.

This project streamlines administrative tasks, provides valuable data insights through dashboards, and ensures the integrity of attendance records.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### 💡 Key Features

* **⚡ Fast Facial Recognition:** Mark attendance for an entire class from a single image.
* **🔒 Anti-Spoofing:** Built-in liveness detection prevents using photos or videos for proxy attendance.
* **👤 Role-Based Access:** Secure, separate dashboards for **Admins**, **Teachers**, and **Students**.
* **🧑‍🎓 Student Portal:** Students can log in to view their detailed attendance percentages and reports for all their subjects.
* **🧑‍🏫 Teacher Portal:**
    * Take attendance via image upload or live camera.
    * View attendance dashboards and lecture trends.
    * Mark attendance manually for exceptions.
    * Download comprehensive attendance reports in **CSV** and **PDF** formats.
* **🛠️ Admin Portal:**
    * Full control over user management (Create, Delete Students/Teachers).
    * Manage subjects (Create, Delete).
    * Assign teachers to subjects.
    * Enroll or remove students from subjects in bulk.
* **📊 Data & Analytics:**
    * Dashboards show overall attendance percentages, lecture-wise trends, and total student/lecture counts.
    * Automatically generates a "Defaulter List" for students below a set attendance threshold.
* **📧 Email Notifications:** Automatically send low-attendance warnings to defaulters with a single click.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### 🔧 Built With

This project is built with a modern, all-Python tech stack.

* [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
* [![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
* [![DeepFace](https://img.shields.io/badge/DeepFace-4C88EF?style=for-the-badge&logo=face&logoColor=white)](https://github.com/serengil/deepface)
* [![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
* [![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/index.html)
* [![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ⚙️ Getting Started

Follow these steps to get a local copy up and running.

### Prerequisites

You must have Python (3.9+ recommended) and Git installed on your system.

* **Python**
    ```sh
    [https://www.python.org/downloads/](https://www.python.org/downloads/)
    ```
* **Git**
    ```sh
    [https://git-scm.com/downloads](https://git-scm.com/downloads)
    ```

### Installation

1.  **Clone the repository**
    ```sh
    git clone [https://github.com/krishujeniya/Hajri.ai.git](https://github.com/krishujeniya/Hajri.ai.git)
    cd Hajri.ai
    ```

2.  **Create and activate a virtual environment** (Recommended)
    * On macOS/Linux:
        ```sh
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    * On Windows:
        ```sh
        python -m venv .venv
        .\.venv\Scripts\activate
        ```

3.  **Create a `requirements.txt` file**
    Create a new file named `requirements.txt` and paste the following libraries into it:
    ```txt
    streamlit
    streamlit-authenticator
    deepface
    pandas
    pillow
    python-dotenv
    albumentations
    fpdf
    opencv-python-headless
    ```

4.  **Install the required packages**
    ```sh
    pip install -r requirements.txt
    ```

5.  **Create an environment file**
    Create a file named `.env` in the project's root directory. This is for your secret keys and passwords.
    * **Note:** For `SENDER_PASSWORD`, it's highly recommended to use a 16-digit "App Password" from your Google account, not your regular password.
    ```env
    # --- App ---
    SECRET_KEY="your_random_secret_key_123"

    # --- Default Admin ---
    ADMIN_USERNAME="admin"
    ADMIN_PASSWORD="changeme123"

    # --- Gmail for Notifications ---
    SENDER_EMAIL="your-email@gmail.com"
    SENDER_PASSWORD="your-16-digit-app-password"
    ```

6.  **Run the app**
    ```sh
    streamlit run app.py
    ```
    Your app will now be running at `http://localhost:8501`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🖥️ Usage

1.  **First-Time Login:**
    * Open `http://localhost:8501`.
    * Log in as the admin using the credentials you set in your `.env` file (e.g., `admin` / `changeme123`).

2.  **Register a Student:**
    * Go to the **"Register User"** tab.
    * Select the "student" role.
    * Fill in the details. After clicking "Create User", the app will guide you to capture 10 photos.
    * The AI model will automatically train on these images.

3.  **Take Attendance:**
    * Go to the **"Take Attendance"** tab.
    * Select a subject and create a new lecture.
    * Upload a photo of the class or use the camera input.
    * The system will analyze the photo, mark "Present" for recognized students, and show you the results.
    * You can manually correct any errors before clicking "Save Verified Attendance".

4.  **View Reports:**
    * Go to the **"Dashboard"** tab to see stats, trends, and the defaulter list.
    * You can download full reports as **CSV** or **PDF**.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📜 License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🙏 Acknowledgments

This project wouldn't be possible without these incredible open-source libraries:

* [Streamlit](https://streamlit.io/)
* [DeepFace](https://github.com/serengil/deepface)
* [Streamlit-Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator)
* [Pandas](https://pandas.pydata.org/)
* [Pillow](https://python-pillow.org/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
