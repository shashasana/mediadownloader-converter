
# Simple script to disable history loading
with open('downloader_qt.py', 'r') as f:
    content = f.read()

# Replace the problematic line
old_line = '        QTimer.singleShot(50, self.load_history)'
new_line = '        # DISABLED - causes UI freeze: QTimer.singleShot(50, self.load_history)'

if old_line in content:
    content = content.replace(old_line, new_line)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("SUCCESS: Disabled history loading on download complete (line 1187)")
else:
    print("ERROR: Could not find the line to replace")
    print("Looking for:", repr(old_line))
