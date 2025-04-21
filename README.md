# AI Drawing Assistant (DrawR)

## Overview

DrawR is a Flask-based web application designed to assist users with comic book style drawing by providing real-time feedback and generating reference images. It uses a webcam feed, Google's Gemini API for analysis and prompt generation, and Google's Vertex AI Imagen for image generation.

**Disclaimer:** The Python and frontend code for this project was generated entirely by an AI assistant (GitHub Copilot) based on user prompts and iterative refinement during development.

## Features

*   **Live Camera Feed:** Displays the user's drawing area via webcam.
*   **AI Critique:** Analyzes the current drawing using Gemini, providing constructive feedback on technique, anatomy, and perspective.
*   **Reference Image Generation:**
    1.  Describes the user's last analyzed drawing using Gemini.
    2.  Combines the description and the critique to generate a detailed text prompt using Gemini.
    3.  Generates a new reference image based on this prompt using Vertex AI Imagen, aiming to correct issues while maintaining the original style/subject.
*   **Text-to-Speech (TTS):** Reads out AI feedback (configurable).
*   **Session History:** Remembers recent feedback to provide context-aware suggestions.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd DrawR
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You may need to create a `requirements.txt` file first using `pip freeze > requirements.txt`)*
4.  **Set up API Keys and Credentials:**
    *   **Google Cloud / Vertex AI:**
        *   Create a Google Cloud project.
        *   Enable the "Vertex AI API" and "Cloud Storage" APIs.
        *   Create a Service Account with the "Vertex AI User" role (and potentially "Storage Object Admin" if using Cloud Storage for images later).
        *   Download the JSON key file for this service account.
    *   **Google AI / Gemini:**
        *   Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   **Create `.env` file:** Create a file named `.env` in the project root directory (`DrawR/DrawR/`) and add your credentials:
        ```dotenv
        # .env
        VISION_API_KEY=YOUR_GEMINI_API_KEY_HERE
        VISION_API_URL=https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro-002:generateContent # Or other compatible model
        VISION_SYSTEM_PROMPT=You are an expert comic book art assistant... # Keep or modify the default prompt
        FLASK_SECRET_KEY=generate_a_strong_random_secret_key

        # Google Cloud Vertex AI Configuration
        VERTEX_PROJECT_ID="YOUR_GOOGLE_CLOUD_PROJECT_ID"
        VERTEX_LOCATION="us-central1" # Or your preferred region
        # Set the *absolute* path to your downloaded service account key file
        GOOGLE_APPLICATION_CREDENTIALS="C:/path/to/your/downloaded-service-account-key.json"
        ```
    *   **Place Service Account Key:** Ensure the service account JSON key file (e.g., `downloaded-service-account-key.json`) exists at the path specified in `GOOGLE_APPLICATION_CREDENTIALS`. **Do not commit this key file to Git.** The `.gitignore` file should prevent this if named correctly.

5.  **Run the application:**
    ```bash
    python app.py
    ```
6.  Open your web browser and navigate to `http://localhost:5000`.

## Usage

1.  Position your drawing under the webcam.
2.  Click "Request Assistance" to get feedback on your current drawing. The analyzed image will appear on the right.
3.  Click "Generate Reference" to generate a new image based on the analysis and critique of the last analyzed drawing. The generated image will replace the analyzed image on the right.
4.  Use the TTS controls and prompt input as needed.
5.  Click "Restart Session" to clear the AI's memory of previous critiques.