# Changelog

## [Unreleased] - 2024-XX-XX (AI Development Cycle)

### Added

*   Initial Flask application structure.
*   Camera module (`modules/camera.py`) for webcam access using OpenCV.
*   Vision API module (`modules/vision_api.py`) initially using Gemini for image analysis/critique.
*   Text-to-Speech module (`modules/text_to_speech.py`) using `pyttsx3`.
*   Drawing Analyzer module (`modules/drawing_analyzer.py`) for basic response processing.
*   Vertex Imagen module (`modules/vertex_imagen.py`) for image generation/editing attempts.
*   Basic Flask routes for UI, video feed, settings, and AI interactions.
*   Socket.IO integration for real-time feedback updates.
*   Basic HTML template (`templates/index.html`) and CSS (`static/css/main.css`).
*   `.env` file support for API keys and configuration.
*   Logging setup.
*   Functionality to save snapped images.
*   Session history for contextual feedback.
*   Launcher script (`launcher.py`) using `pywebview` (experimental).
*   `.gitignore` file.
*   `README.md` file.
*   `CHANGELOG.md` file.

### Changed

*   **Image Generation Strategy:** Shifted from attempting direct image editing/completion (using Vertex AI `edit_image` or REST `predict` on capability models) to a multi-step text-to-image generation process:
    1.  Get critique (Gemini).
    2.  Get detailed description (Gemini).
    3.  Refine text prompt based on description and critique (Gemini).
    4.  Generate new reference image from refined text prompt (Vertex AI `generate_images` with `imagen-3.0-generate-002`).
*   **Vertex Imagen Module:** Refactored multiple times to try different Vertex AI models (`imagegeneration@006`, `imageedit-generation-001`, `imagen-3.0-capability-001`), different access methods (SDK `edit_image`, REST `predict`), and finally settled on SDK `generate_images` for the text-to-image approach.
*   **Vision API Module:** Added methods `get_image_description` and `refine_generation_prompt`. Refactored API calling logic into `_call_gemini_api`.
*   **App Routes:** Renamed `/complete_drawing` to `/generate_reference` and updated its logic significantly. Modified `/request_assistance` to store the last critique.
*   **Frontend:** Renamed "Complete Drawing" button to "Generate Reference". Updated JavaScript to call the new endpoint and handle the `reference_image_ready` socket event. Modified UI to display the generated reference image in the "Last Analyzed Image" pane.
*   **Dependencies:** Updated and aligned `google-cloud-aiplatform`, `vertexai`, and related libraries multiple times to resolve errors and compatibility issues.

### Fixed

*   Numerous `ImportError`, `TypeError`, `AttributeError`, `InvalidArgument`, and `NotFound` errors related to Vertex AI SDK versions, model IDs, API parameters, and response object structures during the iterative development of the image editing/generation feature.
*   Dependency conflicts between `vertexai` and `google-cloud-aiplatform`.
*   Syntax errors introduced during code generation/modification.
*   Frontend logic for enabling/disabling buttons and updating image displays.
*   Handled `ImageGenerationResponse` object correctly instead of treating it as a list.
