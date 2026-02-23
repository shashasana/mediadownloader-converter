with open('downloader_qt.py', 'r') as f:
    lines = f.readlines()

# Find the line number
for i, line in enumerate(lines):
    if 'QTimer.singleShot(50, self.load_history)' in line:
        print(f"Found at line {i+1}: {line.strip()}")
        # Comment it out
        lines[i] = lines[i].replace(
            'QTimer.singleShot(50, self.load_history)',
            '# REMOVED - causes freeze: QTimer.singleShot(50, self.load_history)'
        )
        print(f"Changed to: {lines[i].strip()}")
        break

# Write back
with open('downloader_qt.py', 'w') as f:
    f.writelines(lines)

print("✓ Done - history loading on completion disabled")
