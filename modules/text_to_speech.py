import pyttsx3
import logging
import threading
import os
import time

logger = logging.getLogger(__name__)

class TextToSpeech:
    """Class to handle text-to-speech conversion"""
    
    def __init__(self, voice_id=None, rate=150, volume=0.8):
        """
        Initialize the TTS engine
        
        Args:
            voice_id (str, optional): Voice ID to use
            rate (int): Speech rate (words per minute)
            volume (float): Volume level (0.0 to 1.0)
        """
        self.engine = None
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume
        self.enabled = os.getenv('TTS_ENABLED', 'true').lower() == 'true'
        self.speaking_thread = None
        self.engine_lock = threading.Lock()  # Use a lock to prevent multiple threads trying to use runAndWait simultaneously
        self.stop_requested = threading.Event()
        
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice properties
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            
            # Set voice if specified, otherwise use system default
            if voice_id:
                self.engine.setProperty('voice', voice_id)
            
            logger.info("Text-to-speech engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize text-to-speech engine: {e}")
            self.enabled = False
    
    def speak(self, text, async_mode=True):
        """
        Convert text to speech
        
        Args:
            text (str): Text to convert to speech
            async_mode (bool): Whether to run in async mode
        """
        if not self.enabled or not self.engine:
            logger.warning("TTS is disabled or not properly initialized")
            return False

        # Stop any currently speaking thread (simple version)
        self.stop_speech()
        
        try:
            if async_mode:
                # Ensure previous thread is finished before starting a new one
                if self.speaking_thread and self.speaking_thread.is_alive():
                    logger.info("Waiting for previous TTS thread to finish...")
                    self.speaking_thread.join(timeout=0.5)  # Wait briefly

                logger.info(f"Starting new TTS thread for: '{text[:30]}...'")
                self.speaking_thread = threading.Thread(target=self._speak_thread, args=(text,))
                self.speaking_thread.daemon = True
                self.speaking_thread.start()
                return True
            else:
                # Synchronous mode
                with self.engine_lock:  # Protect synchronous calls too
                    logger.info(f"Speaking synchronously: '{text[:30]}...'")
                    self.engine.say(text)
                    self.engine.runAndWait()
                    logger.info("Synchronous speech finished.")
                return True
        except Exception as e:
            logger.error(f"Error starting text-to-speech: {e}")
            return False

    def stop_speech(self):
        """Stop any currently playing speech (simple version)."""
        try:
            # This might interrupt the current utterance
            self.engine.stop()
            logger.info("Called engine.stop()")
        except Exception as e:
            logger.error(f"Error calling engine.stop(): {e}")
        # We don't explicitly manage the thread stop here anymore,
        # relying on the next speak call or thread completion.

    def _speak_thread(self, text):
        """Thread target for asynchronous speech."""
        # Acquire lock to ensure only one thread uses runAndWait at a time
        acquired = self.engine_lock.acquire(timeout=0.1)  # Try to acquire lock briefly
        if not acquired:
            logger.warning("Could not acquire TTS engine lock, skipping speech.")
            return

        try:
            logger.info(f"TTS thread acquired lock, speaking: '{text[:30]}...'")
            self.engine.say(text)
            self.engine.runAndWait()
            logger.info("TTS thread finished speaking and runAndWait.")
        except RuntimeError as e:
            logger.error(f"TTS thread RuntimeError (likely loop issue): {e}")
        except Exception as e:
            logger.error(f"Error in TTS thread: {e}")
        finally:
            # Ensure the lock is always released
            self.engine_lock.release()
            logger.info("TTS thread released lock.")
    
    def get_available_voices(self):
        """
        Get a list of available voices with names and IDs.

        Returns:
            list: List of dictionaries [{"name": name, "id": id}]
        """
        if not self.engine:
            return []
        voices = self.engine.getProperty('voices')
        return [{"name": v.name, "id": v.id} for v in voices]
    
    def set_voice(self, voice_id):
        """
        Set the voice to use
        
        Args:
            voice_id (str): Voice ID to use
            
        Returns:
            bool: Success status
        """
        if not self.engine:
            return False
            
        try:
            self.engine.setProperty('voice', voice_id)
            self.voice_id = voice_id
            return True
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False

    def set_voice_by_name(self, name_substring):
        """Set the voice by searching for a substring in the voice name."""
        if not self.engine:
            return False
        found_voice = None
        for voice in self.engine.getProperty('voices'):
            if name_substring.lower() in voice.name.lower():
                found_voice = voice
                break

        if found_voice:
            try:
                self.engine.setProperty('voice', found_voice.id)
                self.voice_id = found_voice.id
                logger.info(f"TTS voice set to: {found_voice.name} (ID: {found_voice.id})")
                return True
            except Exception as e:
                logger.error(f"Error setting voice to {found_voice.name}: {e}")
                return False
        else:
            logger.warning(f"No matching voice found for: {name_substring}")
            voices = self.engine.getProperty('voices')
            available_names = [v.name for v in voices]
            logger.info(f"Available voices: {available_names}")
            return False
    
    def set_rate(self, rate):
        """Set speech rate"""
        if not self.engine:
            return False
            
        try:
            self.engine.setProperty('rate', rate)
            self.rate = rate
            logger.info(f"TTS rate property set to {rate}") # Add log for confirmation
            return True
        except Exception as e:
            logger.error(f"Error setting rate: {e}")
            return False
    
    def set_volume(self, volume):
        """Set speech volume"""
        if not self.engine:
            return False
            
        try:
            self.engine.setProperty('volume', volume)
            self.volume = volume
            return True
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False