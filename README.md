# Network Traffic Monitor

A lightweight network traffic monitoring tool that displays real-time upload and download speeds. The application runs in a compact window and can be minimized to the system tray.

## Features

- Real-time network speed monitoring
- Compact, draggable window
- System tray integration
- Adjustable opacity
- Network adapter selection

## Requirements

- Windows OS
- Python 3.12+ (for development)
- Required packages (listed in requirements.txt)

## Installation

### Using the Executable
1. Download the latest release
2. Extract the zip file
3. Run `NetworkMonitor.exe`

### Development Setup
1. Clone the repository
```bash
git clone https://github.com/yourusername/network-monitor.git
cd network-monitor
```

2. Install requirements
```bash
pip install -r requirements.txt
```

3. Run the application
```bash
python net_monitor.py
```

## Building the Executable
To build the executable yourself:
```bash
pyinstaller net_monitor.spec
```
The executable will be created in the `dist` directory.

## Usage
- The main window displays upload and download speeds
- Right-click the window for options:
  - Minimize to tray
  - Adjust opacity
  - Select network adapter
  - Exit
- Left-click and drag to move the window
- The window stays on top of other windows for easy monitoring

## License
MIT License - feel free to use and modify as needed. 