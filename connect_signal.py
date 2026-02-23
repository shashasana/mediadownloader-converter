with open('downloader_qt.py', 'r') as f:
    content = f.read()

old = '''        self.manager.subscribe("download_progress", self.on_download_progress)
        self.manager.subscribe("download_completed", self.on_download_completed)'''

new = '''        self.manager.subscribe("download_progress", self.on_download_progress)
        # Emit signal instead of calling directly to ensure it runs on main thread
        self.download_completed_signal.connect(self.on_download_completed)
        self.manager.subscribe("download_completed", lambda: self.download_completed_signal.emit())'''

if old in content:
    content = content.replace(old, new)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("✓ Connected download_completed_signal to on_download_completed")
else:
    print("✗ Could not find the code")
