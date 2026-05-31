"""
Storage Reusable Infrastructure Client
Handles physical file writes and directory management externalized to the Infra storage directories.
"""

import os
from src.shared.config import config

class StorageClient:
    def __init__(self):
        self.report_path = config.REPORT_PATH
        self.artifact_path = config.ARTIFACT_PATH
        self.archive_path = config.ARCHIVE_PATH
        self.log_path = config.LOG_PATH
        self.chats_path = getattr(config, "CHATS_PATH", os.path.join(config.STORAGE_ROOT, "chats"))
        self._ensure_paths()

    def _ensure_paths(self):
        """Ensures that all configured infrastructure storage directories exist physically on disk."""
        for path in [self.report_path, self.artifact_path, self.archive_path, self.log_path, self.chats_path]:
            if path:
                os.makedirs(path, exist_ok=True)

    def get_reports_dir(self) -> str:
        return self.report_path

    def get_artifacts_dir(self) -> str:
        return self.artifact_path

    def get_archives_dir(self) -> str:
        return self.archive_path

    def get_logs_dir(self) -> str:
        return self.log_path

    def get_chats_dir(self) -> str:
        return self.chats_path

    def save_file(self, target_dir: str, filename: str, content: str) -> str:
        """Helper to physically write content to a target directory file."""
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
