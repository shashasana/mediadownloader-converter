"""Download state management"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Callable
from enum import Enum

class DownloadStatus(Enum):
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

@dataclass
class DownloadTask:
    """Represents a single download task"""
    url: str
    path: str
    format_choice: str
    platform: str = ""
    thumbnail_path: str = ""
    thumbnail_url: str = ""
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    file_size: str = "Unknown"
    speed: str = "0 B/s"
    eta: str = "Calculating..."
    start_time: datetime = field(default_factory=datetime.now)
    process: any = None
    speed_history: list = field(default_factory=list)
    eta_history: list = field(default_factory=list)
    last_error: str = ""
    
    def to_dict(self):
        """Convert to dictionary for history storage"""
        import os
        return {
            "file": os.path.basename(self.path),
            "location": os.path.dirname(self.path),
            "url": self.url,
            "format": self.format_choice,
            "status": self.status.value,
            "timestamp": self.start_time.isoformat()
        }

class DownloadManager:
    """Manages download queue and state"""
    
    def __init__(self, max_downloads: int = 10):
        self.queue: List[DownloadTask] = []
        self.active_downloads: List[DownloadTask] = []
        self.history: List[Dict] = []
        self.max_downloads = max_downloads
        self.callbacks: Dict[str, List[Callable]] = {
            "queue_updated": [],
            "download_started": [],
            "download_progress": [],
            "download_completed": [],
            "history_updated": []
        }
        self._lock = threading.Lock()
    
    def add_task(self, task: DownloadTask) -> bool:
        """Add a task to the queue"""
        with self._lock:
            # Separate max queue limit from max concurrent limit
            if len(self.queue) + len(self.active_downloads) >= 1000:
                return False
            self.queue.append(task)
            self._notify("queue_updated")
            return True
    
    def get_next_task(self) -> DownloadTask:
        """Get next task from queue"""
        with self._lock:
            if self.queue:
                task = self.queue.pop(0)
                self.active_downloads.append(task)
                self._notify("download_started")
                return task
            return None
    
    def update_progress(self, task: DownloadTask, progress: float, speed: str = "", eta: str = ""):
        """Update download progress"""
        with self._lock:
            task.progress = progress
            if speed:
                task.speed = speed
            if eta:
                task.eta = eta
            self._notify("download_progress")
    
    def complete_task(self, task: DownloadTask, success: bool = True):
        """Mark task as completed"""
        with self._lock:
            task.status = DownloadStatus.COMPLETED if success else DownloadStatus.FAILED
            if task in self.active_downloads:
                self.active_downloads.remove(task)
            
            # Add to history
            self.history.insert(0, task.to_dict())
            if len(self.history) > 50:  # Keep last 50
                self.history.pop()
            
            self._notify("download_completed")
            self._notify("history_updated")

    def cancel_task(self, task: DownloadTask):
        """Cancel a running or queued task"""
        with self._lock:
            task.status = DownloadStatus.CANCELLED
            if task in self.queue:
                self.queue.remove(task)
            if task in self.active_downloads:
                self.active_downloads.remove(task)
            self.history.insert(0, task.to_dict())
            if len(self.history) > 50:
                self.history.pop()
            self._notify("download_completed")
            self._notify("history_updated")

    def pause_task(self, task: DownloadTask):
        """Pause a task"""
        with self._lock:
            task.status = DownloadStatus.PAUSED
            if task in self.active_downloads:
                self.active_downloads.remove(task)
            self._notify("download_progress")

    def resume_task(self, task: DownloadTask):
        """Resume a paused task"""
        with self._lock:
            task.status = DownloadStatus.QUEUED
            if task not in self.queue:
                self.queue.insert(0, task)
            self._notify("queue_updated")

    def find_task_by_url(self, url: str):
        """Find task by URL"""
        with self._lock:
            for task in self.queue + self.active_downloads:
                if task.url == url:
                    return task
        return None
    
    def subscribe(self, event: str, callback: Callable):
        """Subscribe to state changes"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _notify(self, event: str):
        """Notify all subscribers"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in callback: {e}")
    
    def is_queue_available(self) -> bool:
        """Check if queue has space"""
        with self._lock:
            return len(self.queue) + len(self.active_downloads) < 1000
    
    def get_active_count(self) -> int:
        """Get number of active downloads"""
        with self._lock:
            return len(self.active_downloads)
    
    def get_queue_count(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self.queue)
