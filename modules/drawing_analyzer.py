import logging
import json
import time
import os
import re

logger = logging.getLogger(__name__)

class DrawingAnalyzer:
    """Class to analyze and process vision API responses about drawings"""
    
    def __init__(self):
        """Initialize the drawing analyzer"""
        self.drawing_history = []
        self.save_history = os.getenv('SAVE_DRAWING_HISTORY', 'true').lower() == 'true'
        self.history_dir = 'drawing_history'
        
        # Create history directory if needed
        if self.save_history and not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
            
        logger.info("Drawing analyzer initialized")
    
    def process_response(self, api_response):
        """
        Process the raw API response into structured feedback
        
        Args:
            api_response (dict): Raw response from the vision API
        
        Returns:
            dict: Processed analysis with text and metadata
        """
        # Extract the text content from the response
        text = api_response.get('text', '')
        
        # Clean up text (remove excessive newlines, etc.)
        text = self._clean_text(text)
        
        # Extract key insights if any
        insights = self._extract_insights(text)
        
        # Build the result object
        result = {
            'text': text,
            'timestamp': int(time.time()),
            'insights': insights,
            'speak': True  # Default to speaking the response
        }
        
        # Condense text for speech if it's very long
        if len(text) > 500:
            result['speech_text'] = self._condense_for_speech(text)
            result['speak'] = True
        
        # Save to history if enabled
        if self.save_history:
            self._save_to_history(result)
        
        return result
    
    def _clean_text(self, text):
        """Clean up text for better presentation"""
        # Replace multiple newlines with double newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure text doesn't start with common AI preambles
        text = re.sub(r'^(I can see that|Looking at your drawing|Based on the image|From what I can observe)', '', text)
        text = text.strip()
        
        return text
    
    def _extract_insights(self, text):
        """Extract key insights from text using simple heuristics"""
        insights = {
            'techniques': [],
            'suggestions': [],
            'detected_elements': []
        }
        
        # Look for techniques mentioned
        technique_patterns = [
            r'using (\w+\s\w+) technique',
            r'(\w+\s\w+) technique',
            r'technique of (\w+\s\w+)'
        ]
        
        for pattern in technique_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            insights['techniques'].extend(matches)
        
        # Look for suggestions
        if 'suggest' in text.lower() or 'try' in text.lower() or 'consider' in text.lower():
            suggestion_sentences = re.findall(r'(?:suggest|try|consider)[^.!?]*[.!?]', text, re.IGNORECASE)
            insights['suggestions'] = suggestion_sentences
        
        # Look for detected elements (very simple approach)
        element_patterns = [
            r'I (see|notice) (\w+)',
            r'there is (\w+\s\w+)',
            r'you\'ve drawn (\w+\s\w+)'
        ]
        
        for pattern in element_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Flatten and extract just the element parts
            elements = [m[-1] if isinstance(m, tuple) else m for m in matches]
            insights['detected_elements'].extend(elements)
        
        # Remove duplicates
        for key in insights:
            insights[key] = list(set(insights[key]))
        
        return insights
    
    def _condense_for_speech(self, text):
        """Create a shorter version suitable for speech"""
        # Get first paragraph
        first_para = text.split('\n\n')[0]
        
        # If still too long, get first few sentences
        if len(first_para) > 300:
            sentences = first_para.split('.')
            condensed = '. '.join(sentences[:3]) + '.'
            return condensed
        
        return first_para
    
    def _save_to_history(self, analysis):
        """Save analysis to history file"""
        try:
            timestamp = analysis['timestamp']
            filename = f"{self.history_dir}/analysis_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            # Keep track of history items
            self.drawing_history.append({
                'timestamp': timestamp,
                'file': filename
            })
            
            # Limit history size
            if len(self.drawing_history) > 100:
                self.drawing_history = self.drawing_history[-100:]
                
        except Exception as e:
            logger.error(f"Error saving analysis history: {e}")
    
    def get_history(self, limit=10):
        """Get recent analysis history"""
        try:
            history_items = []
            
            if not self.save_history:
                return []
                
            # Get list of history files
            files = os.listdir(self.history_dir)
            analysis_files = [f for f in files if f.startswith('analysis_') and f.endswith('.json')]
            
            # Sort by timestamp (newest first)
            analysis_files.sort(reverse=True)
            
            # Load the specified number of items
            for filename in analysis_files[:limit]:
                try:
                    with open(os.path.join(self.history_dir, filename), 'r') as f:
                        item = json.load(f)
                        history_items.append(item)
                except Exception as e:
                    logger.error(f"Error loading history file {filename}: {e}")
            
            return history_items
                
        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []
