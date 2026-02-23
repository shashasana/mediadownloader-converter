with open('downloader_qt.py', 'r') as f:
    lines = f.readlines()

# Find the line with "progress_signal = Signal()"
for i, line in enumerate(lines):
    if 'progress_signal = Signal()' in line and 'download_completed_signal' not in lines[i+1]:
        # Add the new signal after it
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'download_completed_signal = Signal()  # Thread-safe completion\n'
        lines.insert(i + 1, new_line)
        print(f"✓ Added download_completed_signal at line {i+2}")
        break

with open('downloader_qt.py', 'w') as f:
    f.writelines(lines)
print("✓ Done")
