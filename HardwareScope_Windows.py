import subprocess
import tkinter as tk
from tkinter import ttk
import json
import threading
import time


# Helper functions
def run_ps(cmd):
    """Run a PowerShell command and return parsed JSON data."""
    try:
        result = subprocess.check_output(
            ["powershell", "-Command", cmd],
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if result.strip() == "":
            return []
        return json.loads(result)
    except:
        return []

def bytes_to_gb(val):
    """Convert bytes to GB."""
    try:
        return round(int(val) / (1024**3), 2)
    except:
        return 0

def detect_vram(gpu):
    """Detect the larger value between AdapterRAM and DedicatedVideoMemory in GB."""
    a = gpu.get("AdapterRAM", 0)
    d = gpu.get("DedicatedVideoMemory", 0)
    vram = max(int(a or 0), int(d or 0))
    return bytes_to_gb(vram)


# Hardware scan functions
def scan_cpu():
    data = run_ps(
        "Get-CimInstance Win32_Processor | "
        "Select Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed "
        "| ConvertTo-Json"
    )
    cpu_table.delete(*cpu_table.get_children())
    if isinstance(data, dict):
        data = [data]
    for cpu in data:
        cpu_table.insert(
            "",
            "end",
            values=(
                cpu.get("Name"),
                cpu.get("Manufacturer"),
                cpu.get("NumberOfCores"),
                cpu.get("NumberOfLogicalProcessors"),
                f'{cpu.get("MaxClockSpeed")} MHz'
            )
        )

def scan_gpu():
    data = run_ps(
        "Get-CimInstance Win32_VideoController | "
        "Select Name,AdapterRAM,DedicatedVideoMemory,DriverVersion | ConvertTo-Json"
    )
    gpu_table.delete(*gpu_table.get_children())
    if isinstance(data, dict):
        data = [data]
    for gpu in data:
        vram = detect_vram(gpu)
        gpu_table.insert(
            "",
            "end",
            values=(
                gpu.get("Name"),
                f"{vram} GB",
                gpu.get("DriverVersion")
            )
        )

def scan_ram():
    data = run_ps(
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select BankLabel,Capacity,Speed,Manufacturer,PartNumber "
        "| ConvertTo-Json"
    )
    ram_table.delete(*ram_table.get_children())
    total = 0
    if isinstance(data, dict):
        data = [data]
    for r in data:
        size = bytes_to_gb(r.get("Capacity"))
        total += size
        ram_table.insert(
            "",
            "end",
            values=(
                r.get("BankLabel"),
                size,
                r.get("Speed"),
                r.get("Manufacturer"),
                r.get("PartNumber")
            )
        )
    ram_total_label.config(text=f"Total RAM: {round(total,2)} GB")

def scan_storage():
    data = run_ps(
        "Get-CimInstance Win32_LogicalDisk | "
        "Select DeviceID,Size,FreeSpace "
        "| ConvertTo-Json"
    )
    storage_table.delete(*storage_table.get_children())
    if isinstance(data, dict):
        data = [data]
    for s in data:
        total = bytes_to_gb(s.get("Size"))
        free = bytes_to_gb(s.get("FreeSpace"))
        used = round(total - free, 2)
        storage_table.insert(
            "",
            "end",
            values=(
                s.get("DeviceID"),
                total,
                used,
                free
            )
        )

def build_device_tree():
    """Build a device tree similar to Windows Device Manager."""
    tree.delete(*tree.get_children())
    data = run_ps(
        "Get-PnpDevice | Select Class,FriendlyName,Status | ConvertTo-Json"
    )
    if isinstance(data, dict):
        data = [data]
    classes = {}
    for d in data:
        cls = d.get("Class") or "Other"
        if cls not in classes:
            classes[cls] = []
        classes[cls].append(d)
    for cls in sorted(classes.keys(), key=str):
        parent = tree.insert("", "end", text=cls)
        for dev in classes[cls]:
            name = dev.get("FriendlyName") or "Unknown Device"
            status = dev.get("Status") or ""
            tree.insert(parent, "end", text=f"{name} ({status})")


# Monitor scan (all monitors)
def scan_monitors():
    """Scan all connected monitors and show resolution + refresh rate."""
    monitor_table.delete(*monitor_table.get_children())

    # Physical monitors
    physical = run_ps(
        "Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID | ConvertTo-Json"
    )
    if isinstance(physical, dict):
        physical = [physical]

    # Resolution and refresh
    resolution = run_ps(
        "Get-CimInstance Win32_VideoController | "
        "Select CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate | ConvertTo-Json"
    )
    if isinstance(resolution, dict):
        resolution = [resolution]

    for i, monitor in enumerate(physical):
        try:
            res = resolution[i] if i < len(resolution) else {}
            w = res.get("CurrentHorizontalResolution", "N/A")
            h = res.get("CurrentVerticalResolution", "N/A")
            hz = res.get("CurrentRefreshRate", "N/A")
            monitor_table.insert("", "end", values=(
                f"Monitor {i+1}",
                f"{w} x {h}",
                f"{hz} Hz"
            ))
        except Exception:
            monitor_table.insert("", "end", values=(f"Monitor {i+1}", "Unknown", "Unknown"))


# Live hardware graphs
cpu_history = [0]*60
ram_history = [0]*60

def get_cpu_usage():
    """Get CPU usage percentage."""
    try:
        val = subprocess.check_output(
            ["powershell","(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples.CookedValue"],
            text=True
        )
        return float(val.strip())
    except:
        return 0

def get_ram_usage():
    """Get RAM usage percentage."""
    try:
        val = subprocess.check_output(
            ["powershell","(Get-Counter '\\Memory\\% Committed Bytes In Use').CounterSamples.CookedValue"],
            text=True
        )
        return float(val.strip())
    except:
        return 0

def draw_graph(canvas, data):
    """Draw a line graph on the given canvas."""
    canvas.delete("all")
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    step = w / len(data)
    for i in range(len(data)-1):
        x1 = i*step
        x2 = (i+1)*step
        y1 = h - (data[i]/100*h)
        y2 = h - (data[i+1]/100*h)
        canvas.create_line(x1,y1,x2,y2,fill="#27ae60",width=2)

def monitor_loop():
    """Background thread for updating live CPU and RAM graphs."""
    while True:
        cpu = get_cpu_usage()
        ram = get_ram_usage()
        cpu_history.pop(0)
        cpu_history.append(cpu)
        ram_history.pop(0)
        ram_history.append(ram)
        draw_graph(cpu_canvas, cpu_history)
        draw_graph(ram_canvas, ram_history)
        time.sleep(1)


# Full scan
def full_scan():
    scan_cpu()
    scan_gpu()
    scan_ram()
    scan_storage()
    scan_monitors()
    build_device_tree()

def threaded_scan():
    threading.Thread(target=full_scan, daemon=True).start()


# GUI
root = tk.Tk()
root.title("HardwareScope_Windows")
root.geometry("1300x800")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("default")
style.configure("Treeview",background="#2b2b2b",foreground="white",fieldbackground="#2b2b2b",rowheight=26)
style.configure("Treeview.Heading",background="#444",foreground="white")

# TOPBAR WITH SCAN BUTTON
topbar = tk.Frame(root,bg="#1e1e1e")
topbar.pack(fill="x",side="top")
scan_btn = tk.Button(topbar,text="Scan Hardware",command=threaded_scan,
                     bg="#27ae60",fg="white",font=("Segoe UI",11,"bold"),
                     padx=12,pady=4)
scan_btn.pack(side="left",padx=10,pady=8)

# NOTEBOOK
notebook = ttk.Notebook(root)
notebook.pack(fill="both",expand=True)

tab_cpu = tk.Frame(notebook,bg="#1e1e1e")
tab_ram = tk.Frame(notebook,bg="#1e1e1e")
tab_storage = tk.Frame(notebook,bg="#1e1e1e")
tab_devices = tk.Frame(notebook,bg="#1e1e1e")
tab_monitor = tk.Frame(notebook,bg="#1e1e1e")

notebook.add(tab_cpu,text="CPU & GPU")
notebook.add(tab_ram,text="Memory")
notebook.add(tab_storage,text="Storage")
notebook.add(tab_monitor,text="Monitors")
notebook.add(tab_devices,text="Device Manager")

# CPU Table
cpu_table = ttk.Treeview(tab_cpu,columns=("Name","Manufacturer","Cores","Threads","Clock"),show="headings")
for c in ("Name","Manufacturer","Cores","Threads","Clock"):
    cpu_table.heading(c,text=c)
cpu_table.pack(fill="x",padx=10,pady=10)

# GPU Table
gpu_table = ttk.Treeview(tab_cpu,columns=("Name","VRAM","Driver"),show="headings")
gpu_table.heading("Name",text="GPU")
gpu_table.heading("VRAM",text="VRAM")
gpu_table.heading("Driver",text="Driver")
gpu_table.pack(fill="x",padx=10,pady=5)

# Live Hardware Graphs
graph_frame=tk.Frame(tab_cpu,bg="#1e1e1e")
graph_frame.pack(fill="both",expand=True,padx=10,pady=10)
cpu_canvas=tk.Canvas(graph_frame,height=200,bg="#111")
cpu_canvas.pack(fill="x",pady=5)
ram_canvas=tk.Canvas(graph_frame,height=200,bg="#111")
ram_canvas.pack(fill="x",pady=5)

# RAM Table
ram_table=ttk.Treeview(tab_ram,columns=("Slot","SizeGB","Speed","Manufacturer","PartNumber"),show="headings")
for c in ("Slot","SizeGB","Speed","Manufacturer","PartNumber"):
    ram_table.heading(c,text=c)
ram_table.pack(fill="both",expand=True,padx=10,pady=10)
ram_total_label=tk.Label(tab_ram,text="Total RAM",bg="#1e1e1e",fg="white")
ram_total_label.pack()

# Storage Table
storage_table=ttk.Treeview(tab_storage,columns=("Drive","TotalGB","UsedGB","FreeGB"),show="headings")
for c in ("Drive","TotalGB","UsedGB","FreeGB"):
    storage_table.heading(c,text=c)
storage_table.pack(fill="x",padx=10,pady=10)

# Monitor Table
monitor_table=ttk.Treeview(tab_monitor,columns=("Monitor","Resolution","Refresh"),show="headings")
monitor_table.heading("Monitor",text="Monitor")
monitor_table.heading("Resolution",text="Resolution")
monitor_table.heading("Refresh",text="Refresh Rate")
monitor_table.pack(fill="x",padx=10,pady=10)

# Device Tree
tree=ttk.Treeview(tab_devices)
tree.pack(fill="both",expand=True,padx=10,pady=10)

# Start live monitor thread
threading.Thread(target=monitor_loop,daemon=True).start()

root.mainloop()