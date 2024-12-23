import os
import time
import threading
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    help = 'Indexes all user-accessible files dynamically, ignoring sensitive and system-critical files.'

    def handle(self, *args, **kwargs):
        # Directory where the Whoosh index will be stored
        index_dir = "search_index"

        # Schema for indexing: title (file name) and path (file path)
        schema = Schema(title=TEXT(stored=True), path=ID(stored=True))

        # Root directory to monitor (start from system root)
        root_directory = Path("C:/")

        # File types and folders to exclude
        EXCLUDED_FILE_TYPES = [
            ".dll", ".sys", ".tmp", ".log", ".lnk", ".bak", ".iso", ".old", ".vhd", ".vmdk"
        ]
        EXCLUDED_DIRECTORIES = [
            "C:/Windows",
            "C:/Program Files",
            "C:/Program Files (x86)",
            "C:/ProgramData",
            "C:/Users/Default",
            "C:/Users/Default User",
            "C:/Users/Public",
            "C:/Windows/Temp",
            "C:/System Volume Information",
            "C:/Recovery",
            "C:/Boot",
            "C:/Config.Msi",
            "C:/$Recycle.Bin",
            "C:/Users/*/AppData/Local/Temp",
            "C:/Users/*/AppData/Local/Microsoft/Windows/INetCache",
            "C:/Users/*/AppData/Local/VirtualStore",
        ]
        
        # Set a file size threshold (in MB)
        MAX_FILE_SIZE_MB = 100

        # Shared resources
        event_cache = {}
        file_events = []
        index_lock = threading.Lock()

        def is_excluded_directory(directory):
            """Checks if a directory should be excluded."""
            return any(directory.startswith(excluded) for excluded in EXCLUDED_DIRECTORIES)

        def is_excluded_file(file):
            """Checks if a file should be excluded."""
            file_path = Path(file)
            if file_path.exists() and file_path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                return True
            return any(file.endswith(ext) for ext in EXCLUDED_FILE_TYPES)

        def is_hidden(path):
            """Checks if a file or directory is hidden."""
            return Path(path).name.startswith(".")

        def debounce_event(event_type, file_path, debounce_time=1):
            current_time = time.time()
            if (file_path, event_type) in event_cache:
                if current_time - event_cache[(file_path, event_type)] < debounce_time:
                    return False
            event_cache[(file_path, event_type)] = current_time
            return True

        def create_index():
            if not os.path.exists(index_dir):
                os.mkdir(index_dir)
                return create_in(index_dir, schema)
            try:
                return open_dir(index_dir)
            except Exception:
                return create_in(index_dir, schema)

        def index_files(directory, writer):
            for root, _, files in os.walk(directory):
                if is_excluded_directory(root) or is_hidden(root):
                    continue
                for file in files:
                    if not is_excluded_file(file):
                        file_path = os.path.join(root, file)
                        writer.add_document(title=file, path=file_path)

        def start_indexing():
            ix = create_index()
            writer = ix.writer()
            try:
                logger.info(f"Starting indexing from {root_directory}")
                index_files(str(root_directory), writer)
                writer.commit()
                logger.info("Initial indexing complete.")
            except Exception as e:
                logger.error(f"Error during indexing: {e}", exc_info=True)

        class FileEventHandler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory and not is_excluded_file(event.src_path) and debounce_event("created", event.src_path):
                    with index_lock:
                        file_events.append(("created", event.src_path))

            def on_deleted(self, event):
                if not event.is_directory and debounce_event("deleted", event.src_path):
                    with index_lock:
                        file_events.append(("deleted", event.src_path))

            def on_modified(self, event):
                self.on_created(event)

        def process_events():
            while True:
                with index_lock:
                    events_to_process = file_events[:]
                    file_events.clear()

                if events_to_process:
                    ix = open_dir(index_dir)
                    writer = ix.writer()
                    try:
                        for action, file_path in events_to_process:
                            if action == "created":
                                writer.add_document(title=os.path.basename(file_path), path=file_path)
                            elif action == "deleted":
                                writer.delete_by_term("path", file_path)
                        writer.commit()
                        logger.info(f"Processed {len(events_to_process)} events.")
                    except Exception as e:
                        logger.error(f"Error processing events: {e}", exc_info=True)

                time.sleep(5)

        def start_file_monitoring():
            event_handler = FileEventHandler()
            observer = Observer()

            observer.schedule(event_handler, str(root_directory), recursive=True)

            observer.start()
            logger.info("File monitoring started for the system.")

        def open_application(file_path):
            """Utility to open an application."""
            try:
                os.startfile(file_path)
                logger.info(f"Opened application: {file_path}")
            except Exception as e:
                logger.error(f"Failed to open application: {file_path} - {e}", exc_info=True)

        # Run indexing and monitoring
        try:
            logger.info("Starting system-wide indexing and monitoring...")
            start_indexing()
            threading.Thread(target=process_events, daemon=True).start()
            start_file_monitoring()
        except KeyboardInterrupt:
            logger.info("File monitoring stopped.")