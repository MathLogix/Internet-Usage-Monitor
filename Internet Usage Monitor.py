import psutil
import tkinter as tk
from tkinter import ttk, StringVar
from tkinter import Toplevel, Entry, Frame, Button, Label, messagebox, PhotoImage
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading
from PIL import Image, ImageTk
import os
import datetime
import atexit
import re

max_target = 0
target_limits = []
target_popup_open = False
downloaded_amount = 0
downloaded_mb = 0
progress = None

def update_progress():
    global downloaded_amount, progress, target_limits, max_target, target_label, progress_label

    while True:
        if target_limits:
            max_target = max(target_limits) 
            progress["maximum"] = max_target
            progress["value"] = max(downloaded_amount, 0)

            if max_target > 0:
                progress_percent = (downloaded_amount / max_target) * 100
                progress_percent = min(100, progress_percent)
                progress_label.config(text=f"{progress_percent:.1f}%")
            else:
                progress_label.config(text="0%")

            target_label.config(text=f"Max Target: {max_target:.2f} MB")

            for target in target_limits[:]:
                if downloaded_amount >= target:
                    current_time3= datetime.datetime.now().strftime("%H:%M:%S")
                    messagebox.showinfo("Download Target Reached", f"Target Reached {target} MB at {current_time3}")
                    target_limits.remove(target)

        time.sleep(0.1)

def set_target():
    global target_popup_open

    if target_popup_open:
        return  

    target_popup_open = True
    popup = Toplevel(root)
    popup.title("Set Download Target")
    popup.iconbitmap("Internet_Usage_Monitor.ico")
    popup.geometry("350x250")  
    popup.resizable(False, False)

    def on_close():
        global target_popup_open
        target_popup_open = False
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", on_close)

    Label(popup, text="Enter Download Targets (e.g. 5 MB):", font=("Segoe UI", 12)).pack(padx=0, pady=10)

    entries_frame = Frame(popup)
    entries_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def update_popup_size():
        popup.geometry(f"350x{150 + len(entry_widgets) * 30}")

    entry_widgets = [] 
    unit_vars = []

    def add_entry_field(removable=True):
        if len(entry_widgets) >= 3:
            messagebox.showerror("Limit Reached", "Maximum 3 targets allowed.")
            return

        frame = Frame(entries_frame)
        frame.pack(fill="x", pady=5)

        entry = Entry(frame, width=20, font=("Segoe UI", 10))
        entry.grid(row=0, column=0, padx=10)

        unit_var = StringVar()
        unit_combobox = ttk.Combobox(frame, textvariable=unit_var, values=["KB", "MB", "GB"], width=9, state="readonly")
        unit_combobox.grid(row=0, column=1, padx=5)

        unit_vars.append(unit_var)
        root.after(0, lambda v=unit_var: v.set("MB"))

        targetadd_img = PhotoImage(file="targetadd.png")  
        targetadd_button = Button(frame, image=targetadd_img, command=add_entry_field)
        targetadd_button.image = targetadd_img
        targetadd_button.grid(row=0, column=2, padx=5)  

        if removable:
            targetdelete_img = PhotoImage(file="targetdelete.png")  
            targetdelete_button = Button(frame, image=targetdelete_img, command=lambda f=frame, e=entry, u=unit_combobox, v=unit_var: remove_entry(f, e, u, v))
            targetdelete_button.image = targetdelete_img
            targetdelete_button.grid(row=0, column=3, padx=5) 

        entry_widgets.append((entry, unit_combobox, frame))  
        update_popup_size()

    def remove_entry(entry_frame, entry_widget, unit_combobox, unit_var):
        try:
            entry_widgets.remove((entry_widget, unit_combobox, entry_frame))
            unit_vars.remove(unit_var)
            entry_frame.destroy()
            update_popup_size()
        except ValueError:
            print("Error: Entry not found in the list!")

    for _ in range(1):
        add_entry_field(removable=False)

    def save_targets():
        global target_limits, max_target, target_label, progress
        try:
            target_limits = []

            for entry, unit_combobox, _ in entry_widgets:
                text = entry.get().strip().lower() 
                unit = unit_combobox.get() 

                if not text:
                    continue

                match = re.match(r"(\d+(\.\d*)?)$", text)

                if match:
                    target_value = float(match.group(1))  

                    if unit == "KB":
                        target_value /= 1024
                    elif unit == "GB":
                        target_value *= 1024

                    target_limits.append(target_value)
                else:
                    raise ValueError  

            if target_limits:
                max_target = max(target_limits) 
                progress["maximum"] = max_target
                target_label.config(text=f"Max Target: {max_target} MB")
                progress["value"] = min(progress["value"], max_target)

            on_close()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number.")

    targetsave_img = PhotoImage(file="targetsave.png")  
    targetsave_button = Button(popup, image=targetsave_img, command=save_targets)
    targetsave_button.image = targetsave_img
    targetsave_button.pack(pady=10)

def check_download_limit():
    global downloaded_amount, target_limits
    while True:
        if target_limits:
            for target in target_limits[:]:
                if downloaded_amount >= target:
                    current_time3= datetime.datetime.now().strftime("%H:%M:%S")
                    threading.Thread(target=messagebox.showinfo, args=("Download Target Reached", f"Target Reached {target} MB at {current_time3}"), daemon=True).start()
                    target_limits.remove(target)
        time.sleep(0.1)

threading.Thread(target=check_download_limit, daemon=True).start()
threading.Thread(target=update_progress, daemon=True).start()

total_downloaded = 0
total_uploaded = 0
download_speed_mb = 0
upload_speed_mb = 0
max_download_speed_mb = 0  
max_upload_speed_mb = 0

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
file_path = os.path.join(desktop_path, "Internet_Usage_Record.txt")
report_saved = False
session_started = False

def check_previous_session():
    global session_started

    if os.path.exists(file_path): 
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        
        if lines:
            last_line = lines[-1].strip()  
            if last_line == "----------- End of Session -----------":
                session_started = False 
            else:
                session_started = True  
        else:
            session_started = False 

def save_record(event=None):
    global report_saved, session_started, downloaded_mb, current_time, total_downloaded  

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    downloaded_mb = total_downloaded / (1024 * 1024)
    uploaded_mb = total_uploaded / (1024 * 1024)
    download_speed = download_speed_mb
    upload_speed = upload_speed_mb
    record_line = f"{current_time}\tDuration: {elapsed_time_str}\tDownloaded: {downloaded_mb:.3f} MB\tUploaded: {uploaded_mb:.3f} MB\tDownload: {download_speed:.3f} MB/s\tUpload: {upload_speed:.3f} MB/s\n"

    with open(file_path, "a", encoding="utf-8") as file:
        if not report_saved and not session_started:
            file.write("\n=========== New Session ===========\n")
            session_started = True  

        file.write(record_line)

    report_saved = True  

def add_end_marker():
    if report_saved:  
        with open(file_path, "a", encoding="utf-8") as file:
            file.write("----------- End of Session -----------")

is_paused = False

def toggle_pause():
    global is_paused, pause_icon, start_icon 
    is_paused = not is_paused 

    if is_paused:
        pause_button.config(image=start_icon) 
    else:
        pause_button.config(image=pause_icon) 

def setup_ui():
    global pause_button, record_button, pause_icon, start_icon, record_icon, target_icon, target_button, progress, target_label, progress_label

    button_frame = tk.Frame(root)
    button_frame.pack(pady=2)

    pause_icon = Image.open("stop.png")  
    pause_icon = ImageTk.PhotoImage(pause_icon)
    
    start_icon = Image.open("start.png")  
    start_icon = ImageTk.PhotoImage(start_icon)
    
    record_icon = Image.open("report.png")  
    record_icon = ImageTk.PhotoImage(record_icon)

    pause_button = tk.Button(button_frame, image=pause_icon, command=toggle_pause)
    pause_button.pack(side="left", padx=0)
    
    record_button = tk.Button(button_frame, image=record_icon, command=save_record)
    record_button.pack(side="left", padx=0)

    target_icon = Image.open("target.png")  
    target_icon = ImageTk.PhotoImage(target_icon)
    target_button = tk.Button(button_frame, image=target_icon, command=set_target)
    target_button.pack(side="left", padx=0)

    progress = ttk.Progressbar(button_frame, length=200, mode="determinate")
    progress.pack(side="left", padx=10)

    progress_label = tk.Label(button_frame, text="0%", font=("Segoe UI", 10))
    progress_label.pack(side="left", padx=0)

    target_label = tk.Label(button_frame, text= f"Max Target: {max_target} MB", font=("Segoe UI", 10))
    target_label.pack(side="left", padx=0)

last_10_download_speeds = []
last_10_upload_speeds = []

def get_internet_usage():
    net_io = psutil.net_io_counters()
    return net_io.bytes_sent, net_io.bytes_recv

paused_time = 0
pause_start = None

def update_usage():
    global initial_sent, initial_recv, usage_list, speed_list, time_list, start_time, elapsed_time_str, current_time, current_time2
    global last_recv, last_sent, last_time, total_downloaded, total_uploaded
    global total_downloaded, total_uploaded, download_speed_mb, upload_speed_mb
    global paused_time, pause_start, is_paused
    global max_download_speed_mb, max_upload_speed_mb
    global downloaded_amount

    elapsed_time_str = "00:00:00"
    if is_paused:
        if pause_start is None:
            pause_start = time.time()

        paused_duration = int(time.time() - pause_start)
        paused_hours = paused_duration // 3600
        paused_minutes = (paused_duration % 3600) // 60
        paused_seconds = paused_duration % 60
        pause_duration_str = f"  ⏸ {paused_hours:02}:{paused_minutes:02}:{paused_seconds:02}"

        timer_label.config(text=f" {pause_duration_str}" + " " * 26, compound="right")

        root.after(100, update_usage)
        return 

    else:
        if pause_start is not None:
            paused_time += time.time() - pause_start
            pause_start = None

        pause_duration_str = ""

    current_time = time.time()
    elapsed_seconds = int(current_time - start_time - paused_time)
    elapsed_hours = elapsed_seconds // 3600
    elapsed_minutes = (elapsed_seconds % 3600) // 60
    elapsed_seconds = elapsed_seconds % 60
    elapsed_time_str = f"{elapsed_hours:02}:{elapsed_minutes:02}:{elapsed_seconds:02}"

    current_sent, current_recv = get_internet_usage()

    if current_recv < initial_recv:
        initial_recv = current_recv

    if current_sent < initial_sent:
        initial_sent = current_sent

    total_sent = current_sent - initial_sent
    total_recv = current_recv - initial_recv

    if current_recv < last_recv:
        last_recv = current_recv  

    if current_sent < last_sent:
        last_sent = current_sent  

    kb_recv = total_recv / 1024
    mb_recv = kb_recv / 1024
    gb_recv = mb_recv / 1024

    kb_sent = total_sent / 1024
    mb_sent = kb_sent / 1024
    # gb_sent = mb_sent / 1024
    
    time_diff = current_time - last_time if last_time else 1  

    download_speed = (current_recv - last_recv) / time_diff
    download_speed_kb = download_speed / 1024
    download_speed_mb = download_speed_kb / 1024

    upload_speed = (current_sent - last_sent) / time_diff
    upload_speed_kb = upload_speed / 1024
    upload_speed_mb = upload_speed_kb / 1024

    downloaded_amount = mb_recv

    if download_speed_mb > max_download_speed_mb:
        max_download_speed_mb = download_speed_mb

    if upload_speed_mb > max_upload_speed_mb:
        max_upload_speed_mb = upload_speed_mb

    total_downloaded += (current_recv - last_recv)
    total_uploaded += (current_sent - last_sent)

    elapsed_time = current_time - start_time

    last_recv = current_recv
    last_sent = current_sent
    last_time = current_time

    last_10_download_speeds.append(download_speed)
    last_10_upload_speeds.append(upload_speed)

    if len(last_10_download_speeds) > 10:
        last_10_download_speeds.pop(0)
    if len(last_10_upload_speeds) > 10:
        last_10_upload_speeds.pop(0)

    avg_download_speed = sum(last_10_download_speeds) / len(last_10_download_speeds)
    avg_upload_speed = sum(last_10_upload_speeds) / len(last_10_upload_speeds)

    avg_download_speed_kb = avg_download_speed / 1024
    avg_download_speed_mb = avg_download_speed_kb / 1024

    avg_upload_speed_kb = avg_upload_speed / 1024
    avg_upload_speed_mb = avg_upload_speed_kb / 1024

    usage_label.config(text= f"   ⬇ Downloaded:\n          {kb_recv:.3f} KB\n          {mb_recv:.3f} MB\n          {gb_recv:.3f} GB\n   ⬆ Uploaded:\n          {kb_sent:.3f} KB\n          {mb_sent:.3f} MB", compound= "right")

    current_time2= datetime.datetime.now().strftime("       %H:%M:%S\n\n        %Y/%m/%d")

    timer_label.config(text= f"  ⏳ {elapsed_time_str} \n\n {current_time2}", compound= "right")

    speed_label.config(text= f" ⚡Instant Speed:                  \n"
                             f"       ⬇ Download:\n              {download_speed_kb:.3f} KB/s\n              {download_speed_mb:.3f} MB/s\n"
                             f"       ⬆ Upload:\n              {upload_speed_kb:.3f} KB/s\n              {upload_speed_mb:.3f} MB/s", compound= "right")

    avg_speed_label.config(text= f" ⚡Avg Speed (last 10s):      \n"
                                 f"       ⬇ Download:\n              {avg_download_speed_kb:.3f} KB/s\n              {avg_download_speed_mb:.3f} MB/s\n"
                                 f"       ⬆ Upload:\n              {avg_upload_speed_kb:.3f} KB/s\n              {avg_upload_speed_mb:.3f} MB/s", compound= "right")

    max_speed_label.config(text= f"🚀 Max Speed:   ⬇ Download: {max_download_speed_mb:.3f} MB/s   ⬆ Upload: {max_upload_speed_mb:.3f} MB/s  ||  Quick Report => ctrl+r", compound="right")

    usage_list.append(mb_recv)
    speed_list.append(download_speed_mb)
    upload_speed_list.append(upload_speed_mb)
    time_list.append(elapsed_time)

    if len(time_list) > 100:
        usage_list.pop(0)
        speed_list.pop(0)
        upload_speed_list.pop(0)
        time_list.pop(0)

    ax1.clear()
    ax2.clear()
    ax3.clear()
    
    ax1.plot(time_list, usage_list, color='blue', linestyle='-')
    ax1.fill_between(time_list, usage_list, color='blue', alpha=0.1)  
    # ax1.set_title("MB/s")
    ax1.grid(True)
    ax1.set_facecolor("white")
    ax1.text(1.02, 0.5, "Usage\n  MB", rotation=90, va="center", ha="left", fontsize=12, transform=ax1.transAxes)

    ax2.plot(time_list, speed_list, color='green', linestyle='-')
    ax2.fill_between(time_list, speed_list, color='green', alpha=0.1)  
    ax2.grid(True)
    ax2.set_facecolor("white")
    ax2.text(1.02, 0.5, f"Download\n  Speed\n   MB/s ", rotation=90, va="center", ha="left", fontsize=12, transform=ax2.transAxes)

    ax3.plot(time_list, upload_speed_list, color='red', linestyle='-')
    ax3.fill_between(time_list, upload_speed_list, color='red', alpha=0.1)  
    ax3.grid(True)
    ax3.set_facecolor("white")
    ax3.text(1.02, 0.5, f"Upload\nSpeed\n MB/s", rotation=90, va="center", ha="left", fontsize=12, transform=ax3.transAxes)

    canvas.draw()
    root.after(100, update_usage)

initial_sent, initial_recv = get_internet_usage()
start_time = time.time()

usage_list = []
speed_list = []
upload_speed_list = []
time_list = []

last_recv = initial_recv
last_sent = initial_sent
last_time = start_time
total_downloaded = 0
total_uploaded = 0

root = tk.Tk()
root.title("Internet Usage Monitor")
root.iconbitmap("Internet_Usage_Monitor.ico")
# root.geometry("610x700")
root.configure(bg="#F0F0F0")
root.resizable(False, False)

main_frame = Frame(root)
main_frame.pack(expand=True, fill=tk.BOTH)

left_frame = Frame(main_frame)
left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

right_frame = Frame(main_frame)
right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

usage_frame = Frame(left_frame, bg="#E5E5FF")
usage_frame.pack(fill=tk.BOTH)

usage_icon = Image.open("usage.png")  
usage_icon = ImageTk.PhotoImage(usage_icon)

usage_image_label = Label(usage_frame, image=usage_icon, bg="#E5E5FF")
usage_image_label.pack(side=tk.RIGHT, padx=15, pady=25)

usage_label = Label(usage_frame, font=("Segoe UI", 11), bg="#E5E5FF", fg="#333333", anchor="w", justify=tk.LEFT, width=23, height=7)
usage_label.pack(side=tk.RIGHT)

timer_frame = Frame(left_frame, bg="#FBE6FF")
timer_frame.pack(fill=tk.BOTH)

timer_icon = Image.open("timer.png")  
timer_icon = ImageTk.PhotoImage(timer_icon)

timer_image_label = Label(timer_frame, image=timer_icon, bg="#FBE6FF")
timer_image_label.pack(side=tk.RIGHT, padx=15, pady=25)

timer_label = Label(timer_frame, font=("Segoe UI", 11), bg="#FBE6FF", fg="#333333", anchor="w", justify=tk.LEFT, width=23, height=7)
timer_label.pack(side=tk.RIGHT)

speed_frame = Frame(right_frame, bg="#DCE8DC")
speed_frame.pack(fill=tk.BOTH)

speed_icon = Image.open("speed.png")  
speed_icon = ImageTk.PhotoImage(speed_icon)

speed_image_label = Label(speed_frame, image=speed_icon, bg="#DCE8DC")
speed_image_label.pack(side=tk.RIGHT, padx=15, pady=25)

speed_label = Label(speed_frame, font=("Segoe UI", 11), bg="#DCE8DC", fg="#333333", anchor="w", justify=tk.LEFT, width=23, height=7)
speed_label.pack(side=tk.RIGHT)

avg_speed_frame = Frame(right_frame, bg="#FFE5E5")
avg_speed_frame.pack(fill=tk.BOTH)

avg_speed_icon = Image.open("avg_speed.png")  
avg_speed_icon = ImageTk.PhotoImage(avg_speed_icon)

avg_speed_image_label = Label(avg_speed_frame, image=avg_speed_icon, bg="#FFE5E5")
avg_speed_image_label.pack(side=tk.RIGHT, padx=15, pady=25)

avg_speed_label = Label(avg_speed_frame, font=("Segoe UI", 11), bg="#FFE5E5", fg="#333333", anchor="w", justify=tk.LEFT, width=23, height=7)
avg_speed_label.pack(side=tk.RIGHT)

max_speed_label = tk.Label(root, font=("Segoe UI", 10))
max_speed_label.pack(pady=2)

usage_label.pack()
timer_label.pack()
speed_label.pack()
avg_speed_label.pack()
setup_ui()

root.bind("<Control-r>", lambda event: save_record(event))

fig = Figure(figsize=(8, 5), dpi=70)
fig.patch.set_facecolor("#F0F0F0") 
fig.subplots_adjust(top=0.98, bottom=0.07, hspace=0.06)
fig.tight_layout() 
ax1 = fig.add_subplot(311)  
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)  
ax1.grid(True)
ax2.grid(True)
ax3.grid(True)

# ax1.set_xticklabels([])
# ax2.set_xticklabels([])
# ax1.tick_params(bottom=False)
# ax2.tick_params(bottom=False)

# ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

update_usage()
check_previous_session()
atexit.register(add_end_marker)

# root.attributes('-topmost', True) 

# root.after(100, lambda: unit_var.set("MB"))

root.mainloop()