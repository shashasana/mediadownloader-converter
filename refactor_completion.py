with open('downloader_qt.py', 'r') as f:
    content = f.read()

# Find and replace the on_download_completed method
old_method = '''    def on_download_completed(self):
        """Handle download completion"""
        for task_id, task in list(self.task_map.items()):
            if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
                
                # Clean up worker reference
                if hasattr(self, '_download_workers') and task_id in self._download_workers:
                    del self._download_workers[task_id]
        
        # Defer heavy operations to background/timers
        import threading
        
        # Show notification in background thread (non-blocking)
        threading.Thread(target=self._show_notification, daemon=True).start()
        
        # Defer history loading to next event cycle
        QTimer.singleShot(50, self.load_history)
        
        # Defer message box to separate timer to avoid blocking
        QTimer.singleShot(100, self._show_completion_message)
        
        self.process_queue()'''

new_method = '''    def on_download_completed(self):
        """Handle download completion - minimal main thread work"""
        import threading
        
        # Just clean up and update table (fast)
        for task_id, task in list(self.task_map.items()):
            if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
                if hasattr(self, '_download_workers') and task_id in self._download_workers:
                    del self._download_workers[task_id]
        
        # ALL heavy operations in background thread
        threading.Thread(target=self._completion_heavy_work, daemon=True).start()
        self.process_queue()
    
    def _completion_heavy_work(self):
        """Heavy completion work in background thread"""
        import time
        time.sleep(0.1)
        self._show_notification()
        self.load_history()
        QTimer.singleShot(200, self._show_completion_message)'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("✓ Refactored on_download_completed to move heavy work to background thread")
else:
    print("✗ Could not find old method")
