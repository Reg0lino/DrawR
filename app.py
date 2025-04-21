import os
import cv2
import time
import logging
import re
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from dotenv import load_dotenv
from threading import Thread
import traceback  # Ensure traceback is imported
import numpy as np  # Add numpy import for imdecode

# Load environment variables
load_dotenv()

# Ensure necessary directories exist before logging setup
os.makedirs('logs', exist_ok=True)
os.makedirs('captured_images', exist_ok=True)

# Import project modules
from modules.camera import Camera
from modules.vision_api import VisionAPI
from modules.text_to_speech import TextToSpeech
from modules.drawing_analyzer import DrawingAnalyzer
from modules.vertex_imagen import VertexImagen

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
try:
    api_key = os.getenv('VISION_API_KEY')
    api_url = os.getenv('VISION_API_URL')
    system_prompt = os.getenv('VISION_SYSTEM_PROMPT',
        "You are an expert comic book art assistant. Analyze the user's drawing and provide helpful, constructive, and actionable feedback to improve their comic art technique. Focus on clarity, anatomy, perspective, and storytelling. Be concise and supportive."
    )
    logger.info(f"Using Vision API key: {api_key[:8]}... (truncated for security)")
    logger.info(f"Using Vision API URL: {api_url}")
    logger.info(f"Using Vision system prompt: {system_prompt[:60]}...")

    camera = Camera()
    vision_api = VisionAPI(
        api_key=api_key,
        api_url=api_url,
        system_prompt=system_prompt
    )
    tts = TextToSpeech()
    # Example: tts.set_voice_by_name("Aria")  # Uncomment and set to your preferred voice
    drawing_analyzer = DrawingAnalyzer()
    imagen_client = VertexImagen() # Initialize Vertex Imagen client
    logger.info("All components initialized successfully")
except Exception as e:
    logger.error(f"Error initializing components: {e}")
    raise

last_snapped_image = None
last_critique = None  # Store the last critique text
session_history = []

def strip_markdown(text):
    # Remove markdown formatting for TTS clarity
    text = re.sub(r'[`*_>#\-]', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # [text](url) -> text
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)      # ![alt](url) -> (remove)
    return text.strip()

def get_session_prompt():
    """Return a verbose prompt for the first call, then context-aware for subsequent calls."""
    if not session_history:
        return os.getenv('VISION_SYSTEM_PROMPT',
            "You are an expert comic book art assistant. Analyze the user's drawing and provide helpful, constructive, and actionable feedback to improve their comic art technique. Focus on clarity, anatomy, perspective, and storytelling. Be concise and supportive."
        )
    else:
        last = session_history[-1]
        return (
            "Continue providing brief, actionable feedback for the user's comic drawing based on previous suggestions. "
            "Only mention new or ongoing improvements.\n"
            f"Previous suggestion: {last}"
        )

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/last_snapped_image')
def last_snapped_image_route():
    global last_snapped_image
    if last_snapped_image and os.path.exists(last_snapped_image):
        return Response(open(last_snapped_image, 'rb'), mimetype='image/jpeg')
    return '', 404

@app.route('/restart_session', methods=['POST'])
def restart_session():
    global session_history
    session_history = []
    logger.info("Session restarted by user.")
    return jsonify({"status": "success", "message": "Session restarted. The AI will start over and forget previous suggestions."})

@app.route('/set_tts_speed', methods=['POST'])
def set_tts_speed():
    data = request.get_json()
    rate = int(data.get('rate', 150))
    tts.set_rate(rate)
    logger.info(f"TTS rate set to {rate}")
    return jsonify({"status": "success", "rate": rate})

@app.route('/set_tts_enabled', methods=['POST'])
def set_tts_enabled():
    data = request.get_json()
    enabled = bool(data.get('enabled', True))
    tts.enabled = enabled
    logger.info(f"TTS enabled: {enabled}")
    return jsonify({"status": "success", "enabled": enabled})

@app.route('/get_tts_voices', methods=['GET'])
def get_tts_voices():
    voices = tts.get_available_voices()
    return jsonify(voices)

@app.route('/set_tts_voice', methods=['POST'])
def set_tts_voice():
    data = request.get_json()
    voice_id = data.get('voice_id')
    if voice_id:
        success = tts.set_voice(voice_id)
        if success:
            logger.info(f"TTS voice set to ID: {voice_id}")
            return jsonify({"status": "success"})
        else:
            logger.error(f"Failed to set TTS voice ID: {voice_id}")
            return jsonify({"status": "error", "message": "Failed to set voice"}), 500
    return jsonify({"status": "error", "message": "No voice_id provided"}), 400

@app.route('/request_assistance', methods=['POST'])
def request_assistance():
    global last_snapped_image, session_history, last_critique
    try:
        # Capture current frame
        success, frame = camera.get_frame()
        logger.debug("Frame capture attempted for /request_assistance")
        if not success:
            logger.warning("Failed to capture frame for /request_assistance")
            return jsonify({"error": "Failed to capture frame"}), 500
        
        # Save frame for reference
        timestamp = int(time.time())
        frame_path = f"captured_images/request_{timestamp}.jpg"
        cv2.imwrite(frame_path, frame)
        last_snapped_image = frame_path
        logger.debug(f"Frame saved to {frame_path}")

        # Get critique
        current_system_prompt = get_session_prompt()
        logger.info(f"Using session prompt for critique: {current_system_prompt[:80]}...")
        response = vision_api.analyze_drawing(frame)

        critique_text = response.get('text', '')
        if "Error" in critique_text or "failed" in critique_text.lower():
            logger.error(f"Failed to get critique: {critique_text}")
        else:
            last_critique = critique_text
            session_history.append(critique_text)
            session_history = session_history[-5:]

        logger.debug(f"Vision API critique response: {critique_text[:100]}...")

        # Process response for display/TTS
        analysis = drawing_analyzer.process_response({"text": critique_text})

        socketio.emit('assistance_response', {
            'text': analysis['text'],
            'timestamp': timestamp
        })

        if tts.enabled and analysis.get('speak', True):
            tts_text = strip_markdown(analysis['text'])
            tts.speak(tts_text)

        logger.info("Assistance response sent and TTS triggered if enabled.")
        return jsonify({"status": "success", "timestamp": timestamp}), 200

    except Exception as e:
        logger.error(f"Error processing assistance request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/generate_reference', methods=['POST'])
def generate_reference():
    global last_snapped_image, last_critique, vision_api, imagen_client
    logger.info("Received request to generate reference image.")

    if not last_snapped_image or not os.path.exists(last_snapped_image):
        logger.warning("No snapped image found to base reference on.")
        return jsonify({"error": "No image has been snapped yet. Please request assistance first."}), 400

    if not last_critique:
        logger.warning("No critique available for the last snapped image.")
        return jsonify({"error": "No critique available. Please request assistance first."}), 400

    try:
        # Step 1: Get Detailed Description
        logger.info(f"Getting description for image: {last_snapped_image}")
        with open(last_snapped_image, "rb") as f:
            img_bytes = f.read()
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            logger.error("Failed to decode last snapped image for description.")
            return jsonify({"error": "Failed to process snapped image."}), 500

        desc_response = vision_api.get_image_description(frame)
        description_text = desc_response.get('text', '')
        if not description_text or "Error" in description_text:
            logger.error(f"Failed to get image description: {description_text}")
            return jsonify({"error": f"Failed to get image description: {description_text}"}), 500
        logger.info(f"Image Description: {description_text[:100]}...")

        # Step 2: Get Last Critique
        logger.info(f"Using Last Critique: {last_critique[:100]}...")

        # Step 3: Refine Generation Prompt
        logger.info("Refining generation prompt...")
        prompt_response = vision_api.refine_generation_prompt(description_text, last_critique)
        final_image_prompt = prompt_response.get('text', '')
        if not final_image_prompt or "Error" in final_image_prompt:
            logger.error(f"Failed to refine generation prompt: {final_image_prompt}")
            return jsonify({"error": f"Failed to refine generation prompt: {final_image_prompt}"}), 500
        logger.info(f"Final Image Generation Prompt: {final_image_prompt}")

        # Step 4: Generate Image from Text
        logger.info("Calling imagen_client.generate_image_from_text...")
        generated_image_path = imagen_client.generate_image_from_text(
            prompt=final_image_prompt,
            output_dir="generated_images",
            filename_prefix="reference"
        )
        logger.info(f"imagen_client.generate_image_from_text returned: {generated_image_path}")

        # Step 5: Return Result
        if generated_image_path:
            logger.info(f"Reference image generated successfully: {generated_image_path}")
            relative_path = os.path.relpath(generated_image_path, start=os.getcwd())
            web_path = relative_path.replace('\\', '/')
            socketio.emit('reference_image_ready', {'image_path': f"/{web_path}"})
            return jsonify({"status": "success", "message": "Reference image generated.", "image_path": f"/{web_path}"})
        else:
            logger.error("Failed to generate reference image (generate_image_from_text returned None).")
            return jsonify({"error": "Failed to generate reference image using AI."}), 500

    except Exception as e:
        logger.error(f"Error in /generate_reference route handler: {e}", exc_info=True)
        return jsonify({"error": f"Server error during reference generation: {e}"}), 500

@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """Serve generated images from the generated_images directory."""
    logger.debug(f"Serving generated image: {filename}")
    return send_from_directory('generated_images', filename)

def gen_frames():
    """Generate camera frames"""
    while True:
        success, frame = camera.get_frame()
        logger.debug("Frame capture attempted for video feed")
        if not success:
            logger.warning("Failed to capture frame")
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")

if __name__ == '__main__':
    logger.info("Starting AI Drawing Assistant")
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
