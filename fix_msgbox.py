with open('downloader_qt.py', 'r') as f:
    content = f.read()

# Split the message box code into a separate method and defer it
old_method = '''    def _show_completion_ui(self):
        """Show completion notification and update history (deferred)"""
        # Defer heavy operations to background/timers
        import threading
        
        # Show notification in background thread (non-blocking)
        threading.Thread(target=self._show_notification, daemon=True).start()
        
        # Defer history loading to next event cycle
        QTimer.singleShot(50, self.load_history)
        
        # Show message box (non-modal so UI stays responsive)
        if self.manager.history and self.manager.history[0].get("status") == DownloadStatus.COMPLETED.value:
            latest = self.manager.history[0]
            path = os.path.join(latest["location"], latest["file"])
            msg = QMessageBox(self)
            msg.setWindowTitle("Download Complete")
            msg.setText("Open the downloaded file?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setModal(False)
            msg.buttonClicked.connect(lambda btn, p=path: self._open_file_path(p)
                                      if msg.standardButton(btn) == QMessageBox.StandardButton.Yes else None)
            msg.show()'''

new_methods = '''    def _show_completion_message(self):
        """Show completion message box (deferred)"""
        if self.manager.history and self.manager.history[0].get("status") == DownloadStatus.COMPLETED.value:
            latest = self.manager.history[0]
            path = os.path.join(latest["location"], latest["file"])
            msg = QMessageBox(self)
            msg.setWindowTitle("Download Complete")
            msg.setText("Open the downloaded file?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setModal(False)
            msg.buttonClicked.connect(lambda btn, p=path: self._open_file_path(p)
                                      if msg.standardButton(btn) == QMessageBox.StandardButton.Yes else None)
            msg.show()
    
    def _show_completion_ui(self):
        """Show completion notification and update history (deferred)"""
        # Defer heavy operations to background/timers
        import threading
        
        # Show notification in background thread (non-blocking)
        threading.Thread(target=self._show_notification, daemon=True).start()
        
        # Defer history loading and message box to separate timers
        QTimer.singleShot(50, self.load_history)
        QTimer.singleShot(100, self._show_completion_message)'''

if old_method in content:
    content = content.replace(old_method, new_methods)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("✓ Deferred message box with separate timer")
else:
    print("✗ Could not find method")
