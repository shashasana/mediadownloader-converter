with open('downloader_qt.py', 'r') as f:
    lines = f.readlines()

# Find the DownloaderAppQt class signals section and add the missing signal
for i, line in enumerate(lines):
    if 'class DownloaderAppQt' in line:
        # Find the progress_signal line after this
        for j in range(i, min(i+20, len(lines))):
            if 'progress_signal = Signal()' in lines[j]:
                # Check if download_completed_signal is already there
                if 'download_completed_signal' not in lines[j+1]:
                    # Add it
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    new_line = ' ' * indent + 'download_completed_signal = Signal()  # Thread-safe completion\n'
                    lines.insert(j + 1, new_line)
                    print(f"✓ Added download_completed_signal to DownloaderAppQt at line {j+2}")
                break
        break

# Also remove the incorrectly placed one from DownloadWorker
for i, line in enumerate(lines):
    if 'download_completed_signal = Signal()  # Thread-safe completion' in line:
        # Check if this is in DownloadWorker (before DownloaderAppQt)
        found_dlworker = False
        for j in range(max(0, i-20), i):
            if 'class DownloadWorker' in lines[j]:
                found_dlworker = True
                break
        if found_dlworker:
            print(f"✓ Removing wrongly placed signal from DownloadWorker at line {i+1}")
            lines.pop(i)
            break

with open('downloader_qt.py', 'w') as f:
    f.writelines(lines)

print("✓ Fixed signal placement")
