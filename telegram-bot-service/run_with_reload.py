import os
import sys
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart_time = 0
        self.restart_delay = 2  # Seconds to wait before allowing another restart
        self.start_process()

    def start_process(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            logger.info("Process terminated. Restarting...")
        else:
            logger.info("Starting process...")
        
        self.process = subprocess.Popen([sys.executable, "main.py"])
        self.last_restart_time = time.time()

    def on_modified(self, event):
        # Only handle file modification events, not created/moved/deleted
        self._handle_event(event)
    
    def _handle_event(self, event):
        # Skip if this is a directory
        if event.is_directory:
            return
        
        # Skip certain files that shouldn't trigger restart
        if any(pattern in event.src_path for pattern in ["__pycache__", ".pyc", "run_with_reload.py"]):
            return
            
        # Only restart for Python files
        if not event.src_path.endswith('.py'):
            return
            
        # Debounce: prevent restarts in quick succession
        current_time = time.time()
        if current_time - self.last_restart_time < self.restart_delay:
            logger.info(f"Ignoring change to {event.src_path} (too soon after last restart)")
            return
            
        logger.info(f"Change detected: {event.src_path}")
        self.start_process()

if __name__ == "__main__":
    path = "."
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if event_handler.process:
            event_handler.process.terminate()
        observer.stop()
    observer.join() 