from django.apps import AppConfig
from search.management.commands.index_files import Command as IndexCommand
import threading
import os

class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search'

    def ready(self):
        """
        Initializes the application and starts file indexing in a background thread.
        """
        # Prevent repeated execution with Django's autoreload
        if os.environ.get('RUN_MAIN', None) != 'true':
            return

        def run_indexing():
            try:
                print("Starting file indexing...")
                IndexCommand().handle()  # Run the indexing command
                print("File indexing completed.")
            except Exception as e:
                print(f"An error occurred during file indexing: {e}")

        # Start indexing in a background thread
        threading.Thread(target=run_indexing, daemon=True).start()
