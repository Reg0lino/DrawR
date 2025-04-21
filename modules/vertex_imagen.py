import os
from dotenv import load_dotenv
from PIL import Image as PILImage
import io
import logging
import traceback
import vertexai
# Import the necessary SDK classes for image generation
from vertexai.vision_models import ImageGenerationModel, Image
import time

load_dotenv()
logger = logging.getLogger(__name__)

class VertexImagen:
    def __init__(self):
        """Initializes the Vertex AI client using the SDK for image generation."""
        self.project_id = os.getenv("VERTEX_PROJECT_ID")
        self.location = os.getenv("VERTEX_LOCATION", "us-central1")
        # Use the generation model ID from the latest docs
        self.model_id = "imagen-3.0-generate-002"
        if not self.project_id:
            raise ValueError("VERTEX_PROJECT_ID environment variable not set.")

        try:
            # Initialize vertexai library
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"Vertex AI SDK initialized for project {self.project_id} in {self.location}.")

            # Load the image generation model using the SDK
            self.model = ImageGenerationModel.from_pretrained(self.model_id)
            logger.info(f"Vertex AI ImageGenerationModel ({self.model_id}) initialized.")

        except Exception as e:
            logger.error(f"Fatal: Error initializing Vertex AI SDK or Model: {e}")
            logger.error(traceback.format_exc())
            raise

    def generate_image_from_text(self, prompt: str, output_dir: str = "generated_images", filename_prefix: str = "generated") -> str | None:
        """
        Generates an image based on a text prompt using the Vertex AI SDK.

        Args:
            prompt: Text prompt guiding the image generation.
            output_dir: Directory to save the generated image.
            filename_prefix: Prefix for the output filename.

        Returns:
            The file path of the generated image, or None if an error occurred.
        """
        logger.info(f"Generating image via SDK with prompt: '{prompt[:100]}...'")
        os.makedirs(output_dir, exist_ok=True)

        try:
            logger.debug("Sending request via SDK model.generate_images...")
            # generate_images returns a response object
            response = self.model.generate_images(
                prompt=prompt,
                number_of_images=1,
            )
            logger.info("Received response from Vertex AI SDK.")

            # Check if the response object exists and has the .images attribute which is not empty
            if response and hasattr(response, 'images') and response.images:
                # Log the length of the images list within the response object
                logger.info(f"Response contains {len(response.images)} image(s).")
                try:
                    # Access the image bytes from the list within the response object
                    logger.debug("Attempting to access response.images[0]._image_bytes")
                    # Access the .images attribute which should be the list
                    generated_image_bytes = response.images[0]._image_bytes
                    logger.info(f"Successfully accessed image bytes (length: {len(generated_image_bytes)}).")

                    # Save the generated image
                    timestamp = int(time.time()) # Add timestamp for unique filenames
                    output_filename = f"{filename_prefix}_{timestamp}.png"
                    output_path = os.path.join(output_dir, output_filename)

                    logger.debug(f"Attempting to save image to: {output_path}")
                    img = PILImage.open(io.BytesIO(generated_image_bytes))
                    img.save(output_path, format='PNG')
                    logger.info(f"Generated image saved successfully to: {output_path}")
                    return output_path
                except AttributeError as ae:
                    logger.error(f"AttributeError accessing image data from SDK response: {ae}.")
                    # Log the response object itself and its images attribute for inspection
                    logger.error(f"Response object: {response}")
                    if hasattr(response, 'images'):
                        logger.error(f"Response images attribute: {response.images}")
                    logger.error(traceback.format_exc())
                    return None
                except Exception as img_err:
                    logger.error(f"Error processing or saving image data from SDK response: {img_err}")
                    logger.error(traceback.format_exc())
                    return None
            else:
                logger.warning(f"Vertex AI SDK response did not contain expected 'images' data or it was empty.")
                # Log the response object itself for inspection
                logger.warning(f"Response object details: {response}")
                return None

        except Exception as e:
            logger.error(f"Error calling Vertex AI SDK model.generate_images: {e}")
            logger.error(traceback.format_exc())
            return None

# Example usage (for testing purposes)
if __name__ == '__main__':
    print("Running VertexImagen module test...")
    try:
        imagen_client = VertexImagen()
        test_prompt = "Generate a serene landscape with mountains and a lake."
        result_path = imagen_client.generate_image_from_text(test_prompt)
        if result_path:
            print(f"Test successful. Image generated at: {result_path}")
        else:
            print("Test failed. Image generation returned None.")
    except ValueError as ve:
        print(f"Configuration error: {ve}")
    except Exception as ex:
        print(f"An unexpected error occurred during testing: {ex}")