# HardwareScope

**HardwareScope** is a lightweight hardware scanning and monitoring tool for Windows written in Python with **Tkinter GUI**.  
It allows users to inspect CPU, GPU, RAM, Storage, Monitors, and connected devices, along with live CPU/RAM usage graphs.

---

## Features

- **CPU Details:** Name, Manufacturer, Cores, Threads, Clock Speed
- **GPU Details:** Name, VRAM, Driver Version
- **RAM Modules:** Individual slots with size, speed, manufacturer
- **Storage:** Drives with Total, Used, Free space
- **Monitors:** Detects all physical monitors with Resolution + Refresh Rate
- **Device Manager:** Hierarchical device tree similar to Windows Device Manager
- **Live Graphs:** CPU and RAM usage over time

---

## How It Works

1. Uses **PowerShell WMI queries** to retrieve system hardware information.
2. Converts PowerShell JSON output to Python dictionaries.
3. Populates **Tkinter Treeview tables** for each hardware category.
4. **Live graphs** update every second using PowerShell counters (`Get-Counter`).
5. Detects **all physical monitors** using `WmiMonitorID` to improve multi-monitor setups.

---

## Usage

1. Run the Python script on a Windows machine.
2. Click **"Scan Hardware"** to populate all tables and graphs.
3. Navigate tabs to inspect CPU/GPU, Memory, Storage, Monitors, or the Device Manager.

---

## Dependencies

- Python 3.x
- Windows OS (WMI support)
- Tkinter (standard with Python)
- No external libraries required

---

## Notes

- GPU VRAM is detected using `AdapterRAM` and `DedicatedVideoMemory` for better accuracy.
- Monitor detection now works for multiple monitors beyond primary displays.
- Device Manager tree handles devices without class or friendly name to prevent errors.
