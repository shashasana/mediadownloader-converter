
with open('downloader_qt.py', 'r') as f:
    content = f.read()

old = '''        self.history_frame.clear_all()
        for item in self.manager.history[:20]:
            self.history_frame.add_history_item(
                item["file"],
                item["location"],
                item["format"],
                item["status"],
                item["url"]
            )'''

new = '''        # Disable table updates during bulk operation
        self.history_frame.table.setUpdatesEnabled(False)
        try:
            self.history_frame.clear_all()
            for item in self.manager.history[:20]:
                self.history_frame.add_history_item(
                    item["file"],
                    item["location"],
                    item["format"],
                    item["status"],
                    item["url"]
                )
        finally:
            self.history_frame.table.setUpdatesEnabled(True)'''

if old in content:
    content = content.replace(old, new)
    with open('downloader_qt.py', 'w') as f:
        f.write(content)
    print("✓ Optimized load_history() with disabled table updates")
else:
    print("✗ Could not find code to replace")
