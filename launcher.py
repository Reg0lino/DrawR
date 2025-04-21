import webview
import subprocess
import sys
import os
import time
import signal
import threading
import requests # Import requests library

flask_process = None
app_url = "http://localhost:5000" # Make sure this matches the host/port in app.py

# Function to continuously read and print output from a stream
def stream_reader(stream, stream_name):
    try:
        for line in iter(stream.readline, b''):
            print(f"[{stream_name}] {line.decode().strip()}")
        stream.close()
    except Exception as e:
        print(f"Error reading {stream_name}: {e}")

def start_flask_server():
    """Starts the Flask server in a subprocess."""
    global flask_process
    # Ensure the path to python executable and app.py is correct
    python_executable = sys.executable # Use the same python that runs the launcher
    app_script = os.path.join(os.path.dirname(__file__), 'app.py')
    print(f"Starting Flask server: {python_executable} {app_script}")

    # Use Popen to start the server without blocking
    # Use CREATE_NEW_PROCESS_GROUP on Windows to allow clean termination
    kwargs = {}
    if sys.platform == "win32":
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    flask_process = subprocess.Popen(
        [python_executable, app_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False, # Read streams as bytes
        bufsize=1, # Line buffered
        **kwargs
    )
    print(f"Flask server started with PID: {flask_process.pid}")

    # Start threads to read stdout and stderr
    stdout_thread = threading.Thread(target=stream_reader, args=(flask_process.stdout, "Flask stdout"), daemon=True)
    stderr_thread = threading.Thread(target=stream_reader, args=(flask_process.stderr, "Flask stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

def stop_flask_server():
    """Stops the Flask server process."""
    global flask_process
    if flask_process and flask_process.poll() is None: # Check if process exists and is running
        print(f"Stopping Flask server process (PID: {flask_process.pid})...")
        try:
            if sys.platform == "win32":
                # Send CTRL_BREAK_EVENT on Windows, more graceful than terminate/kill
                flask_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Send SIGTERM on Unix-like systems
                flask_process.send_signal(signal.SIGTERM)

            # Wait a bit for graceful shutdown
            flask_process.wait(timeout=5)
            print("Flask server process terminated gracefully.")
        except subprocess.TimeoutExpired:
            print("Flask server did not terminate gracefully, killing...")
            flask_process.kill()
            print("Flask server process killed.")
        except Exception as e:
            print(f"Error stopping Flask server: {e}. Killing...")
            flask_process.kill() # Fallback to kill
            print("Flask server process killed.")
        finally:
            flask_process = None
    else:
        print("Flask server process already stopped or not started.")

def check_server_ready(url, timeout=1):
    """Checks if the server at the URL is responding."""
    try:
        response = requests.get(url, timeout=timeout)
        # Check for a successful status code (e.g., 200 OK)
        if response.status_code == 200:
            print(f"Server at {url} is ready.")
            return True
        else:
            print(f"Server at {url} responded with status: {response.status_code}")
            return False
    except requests.ConnectionError:
        # Server is not yet accepting connections
        return False
    except requests.Timeout:
        # Server took too long to respond
        print(f"Server at {url} timed out.")
        return False
    except Exception as e:
        print(f"Error checking server readiness at {url}: {e}")
        return False

if __name__ == '__main__':
    # Start Flask server in a separate thread
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()

    # Give the server a moment to start up - Replace sleep with active check
    print("Waiting for Flask server to start...")
    max_wait_time = 30 # Maximum seconds to wait for the server
    wait_interval = 1 # Seconds between checks
    start_time = time.time()
    server_ready = False

    while time.time() - start_time < max_wait_time:
        if flask_process and flask_process.poll() is not None:
            print("[Launcher] Flask process terminated unexpectedly while waiting.")
            stop_flask_server()
            sys.exit(1)

        if check_server_ready(app_url):
            server_ready = True
            break
        print(f"Server not ready yet, waiting {wait_interval}s...")
        time.sleep(wait_interval)

    if not server_ready:
        print(f"[Launcher] Flask server did not become ready within {max_wait_time} seconds. Exiting.")
        stop_flask_server()
        sys.exit(1)

    # Check if Flask process terminated prematurely (redundant check after loop, but safe)
    if flask_process and flask_process.poll() is not None:
        print("[Launcher] Flask process terminated unexpectedly before webview started. Check Flask logs above.")
        stop_flask_server() # Clean up just in case
        sys.exit(1) # Exit launcher

    # Create and start the webview window
    print(f"Creating webview window for {app_url}")
    try:
        webview.create_window('AI Drawing Assistant', app_url, width=1024, height=768)
        # Pass the stop_flask_server function to be called when the window is closed
        webview.start(stop_flask_server, debug=True) # Enable pywebview debug logging
    except Exception as e:
        print(f"[Launcher] Error creating or starting webview: {e}")
        stop_flask_server() # Ensure Flask server is stopped if webview fails
        sys.exit(1)

    print("Webview window closed. Exiting launcher.")
