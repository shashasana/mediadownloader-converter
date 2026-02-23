with open('downloader_qt.py', 'r') as f:
    content = f.read()

old_code = '''    def _show_completion_ui(self):
        """Show completion notification and update history (deferred)"""
        # Load history asynchronously
        self.load_history()
        
        if NOTIFY_AVAILABLE and self.settings.get("notifications", True):
            try:
                notification.notify(
                    title="Download Complete",
                    message="Your download has finished!",
                    timeout=5
                )
            except Exception:
                pass'''

new_code = '''    def _show_completion_ui(self):
        """Show completion notification and update history (deferred)"""
        import threading
        
        # Show notification in background thread (non-blocking)
        def show_notif():
            if NOTIFY_AVAILABLE and self.settings.get("notifications", True):
                try:
                    notification.notify(
                        title="Download Complete",
                        message="Your download has finished!",
                        timeout=5
                    )
                except Exception:
                    pass
        
        thread = threading.Thread(target=show_notif, daemon=True)
        thread.start()'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("SUCCESS: Replaced _show_completion_ui method")
else:
    print("ERROR: Could not find old_code in file")
