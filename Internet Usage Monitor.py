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
import ctypes
import subprocess
import datetime
import atexit
import re
import platform
import jdatetime

max_target = 0
target_popup_open = False
popup = None
downloaded_amount = 0
downloaded_mb = 0
progress = None
shutdown_target = None
notification_targets = []
shutdown_targets = []
target_type_dropdown = None

def update_progress():
    global downloaded_amount, progress, max_target, target_label, progress_label, shutdown_target, notification_targets, shutdown_targets

    def refresh_download_ui():
        if progress is None or progress_label is None or target_label is None:
            return

        if notification_targets or shutdown_targets:
            all_targets = notification_targets + shutdown_targets
            max_target = max(all_targets) if all_targets else 0
            progress["maximum"] = max_target
            progress["value"] = max(downloaded_amount, 0)

            if max_target > 0:
                percent = min(100, (downloaded_amount / max_target) * 100)
                progress_label.config(text=f"{percent:.1f}%")
            else:
                progress_label.config(text="0%")

            target_label.config(text=f"Max Target: {max_target:.2f} MB")

            for target in shutdown_targets[:]:
                if downloaded_amount >= target:
                    shutdown_targets.remove(target)
                    threading.Thread(target=shutdown_system(shutdown_type.get()), daemon=True).start()
                    break
        else:
            progress["value"] = 0
            progress["maximum"] = 100
            progress_label.config(text="0%")
            target_label.config(text="No active targets.")

    # while True:
    #     if progress and progress_label and target_label:
    #         progress.after(0, refresh_download_ui)
    #     time.sleep(0.1)

    refresh_download_ui()
    if root.winfo_exists():
        progress.after(100, update_progress)

def set_target():
    global target_popup_open, popup

    if target_popup_open and popup is not None and popup.winfo_exists():
        popup.lift()
        return

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
    # target_type_vars =[]

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

        # target_type_var = StringVar()
        # target_type_combobox = ttk.Combobox(frame, textvariable=target_type_var, values=["Notification", "Shutdown"], width=15, state="readonly")
        # target_type_combobox.grid(row=0, column=2, padx=5)
        # target_type_vars.append(target_type_var)
        # root.after(0, lambda v=target_type_var: v.set("Notification"))
        target_type_combobox = None

        targetadd_img = PhotoImage(file="targetadd.png")  
        targetadd_button = Button(frame, image=targetadd_img, command=add_entry_field, cursor="hand2")
        targetadd_button.image = targetadd_img
        targetadd_button.grid(row=0, column=2, padx=5)

        if removable:
            delete_img = PhotoImage(file="targetdelete.png")
           # # delete_button = Button(frame, image=delete_img, command=lambda f=frame: remove_entry(f, entry, unit_combobox, target_type_combobox), cursor="hand2")
            delete_button = Button(frame, image=delete_img, command=lambda f=frame, e=entry, u=unit_combobox, t=target_type_combobox: remove_entry(f, e, u, t), cursor="hand2")
            delete_button.image = delete_img
            delete_button.grid(row=0, column=3, padx=5)

        entry_widgets.append((entry, unit_combobox, None))
        update_popup_size()

    def remove_entry(entry_frame, entry_widget, unit_combobox, target_type_combobox):
        try:
            entry_widgets.remove((entry_widget, unit_combobox, target_type_combobox))
            entry_frame.destroy()
            update_popup_size()
        except ValueError:
            print("Error: Entry not found in the list!")

    for _ in range(1):
        add_entry_field(removable=False)

    def save_targets():
        global notification_targets, shutdown_targets, max_target, target_label, progress, downloaded_amount
        try:
            notification_targets = []
            
            # print("entry_widgets:", entry_widgets)
            # for i, w in enumerate(entry_widgets):
            #     print(f"{i}: {[type(x) for x in w]}\n\n")
            
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

                    if downloaded_amount >= target_value:
                        target_value += downloaded_amount
                    
                    notification_targets.append(target_value)
                else:
                    raise ValueError("Invalid number format")

            max_target = max(notification_targets + shutdown_targets) if notification_targets + shutdown_targets else 0
            progress["maximum"] = max_target
            progress["value"] = min(progress["value"], max_target)
            target_label.config(text=f"Max Target: {max_target:.2f} MB")

            on_close()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid values for the targets.")

    targetsave_img = PhotoImage(file="targetsave.png")  
    targetsave_button = Button(popup, image=targetsave_img, command=save_targets, cursor="hand2")
    targetsave_button.image = targetsave_img
    targetsave_button.pack(pady=10)

def show_info_popup(target):
    current_time3 = datetime.datetime.now().strftime("%H:%M:%S")
    messagebox.showinfo("Download Target Reached", f"Target Reached {target:.2f} MB at {current_time3}")

def check_download_limit():
    global downloaded_amount, notification_targets, shutdown_targets
    while True:
        if notification_targets:
            for target in notification_targets[:]:
                if downloaded_amount >= target:
                    notification_targets.remove(target)
                    threading.Thread(target=lambda: root.after(0, show_info_popup, target), daemon=True).start()

        if shutdown_targets:
            for target in shutdown_targets[:]:
                if downloaded_amount >= target:
                    shutdown_targets.remove(target)
                    threading.Thread(target=shutdown_system(shutdown_type.get()), daemon=True).start()

        time.sleep(0.1)

threading.Thread(target=check_download_limit, daemon=True).start()
# threading.Thread(target=update_progress, daemon=True).start()

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
        pause_button.config(image=start_icon, cursor="hand2") 
    else:
        pause_button.config(image=pause_icon, cursor="hand2") 

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

    pause_button = tk.Button(button_frame, image=pause_icon, command=toggle_pause, cursor="hand2")
    pause_button.pack(side="left", padx=0)
    
    record_button = tk.Button(button_frame, image=record_icon, command=save_record, cursor="hand2")
    record_button.pack(side="left", padx=0)

    target_icon = Image.open("target.png")  
    target_icon = ImageTk.PhotoImage(target_icon)
    target_button = tk.Button(button_frame, image=target_icon, command=set_target, cursor="hand2")
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
    global initial_sent, initial_recv, usage_list, speed_list, time_list, start_time, elapsed_time_str, current_time, current_time2, current_time3
    global last_recv, last_sent, last_time, total_downloaded, total_uploaded
    global total_downloaded, total_uploaded, download_speed_mb, upload_speed_mb
    global paused_time, pause_start, is_paused
    global max_download_speed_mb, max_upload_speed_mb
    global downloaded_amount, remaining

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

    current_time2= datetime.datetime.now().strftime(" %H:%M:%S")
    current_time3= datetime.datetime.now().strftime(" %Y/%m/%d")

    if remaining is not None and remaining < 0:
        remaining = 0

    if not shutdown_active or shutdown_mode is None:
        timer_label.config(text=f"    ⏳ {elapsed_time_str} \n\n    🕒{current_time2} \n\n    🗓{current_time3}", compound="right")

    else:
        if shutdown_mode == "date":
            if target_time and remaining > 0:
                remaining_time_str = f"{int(remaining // 3600):02}:{int((remaining % 3600) // 60):02}:{int(remaining % 60):02}"
                target_display = target_time.strftime("%Y/%m/%d   %H:%M:%S")
                timer_label.config(text=f"    🎯 {target_display}\n\n    ⚠️ {remaining_time_str}  ({selected_shutdown_type})\n\n    ⏳ {elapsed_time_str}", compound="right")
            else:
                timer_label.config(text=f"    ⏳ {elapsed_time_str} \n\n    🕒{current_time2} \n\n    🗓{current_time3}", compound="right")

        elif shutdown_mode == "download":
            if target_time and remaining > 0:
                remaining_time_str = f"{int(remaining // 3600):02}:{int((remaining % 3600) // 60):02}:{int(remaining % 60):02}"
                target_display = target_time.strftime("%Y/%m/%d   %H:%M:%S")
                timer_label.config(text=f"    🎯 {target_display}\n\n    ⚠️ {remaining_time_str}  ({selected_shutdown_type})\n\n    ⏳ {elapsed_time_str}", compound="right")
            else:
                timer_label.config(text=f"    ⏳ {elapsed_time_str} \n\n    🕒{current_time2}  ({selected_shutdown_type}) \n\n    🗓{current_time3}", compound="right")

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

global remaining, remaining_time_str, shutdown_thread, shutdown_active, target_time, shutdown_mode, cancel_button
remaining = 0
shutdown_thread = None
shutdown_active = False
target_time = None
shutdown_mode = "date"
shutdown_window_open = False
shutdown_win = None

def shutdown_system(shutdown_mode):
    os_type = platform.system()

    try:
        if os_type != "Windows":
            messagebox.showerror("Unsupported OS", "This feature currently supports Windows only.")
            return

        if shutdown_mode == "Shutdown":
            os.system("shutdown /s /t 1")
        elif shutdown_mode == "Hibernate":
            os.system("shutdown /h")
        elif shutdown_mode == "Sleep":
            os.system("powercfg -hibernate off")
            ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
            os.system("powercfg -hibernate on")
        # elif shutdown_mode == "Sleep":
        #     os.system("rundll32.exe powrprof.dll,SetSuspendState 0,0,0")
        # elif shutdown_mode == "Sleep":
        #     os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
        elif shutdown_mode == "Restart":
            os.system("shutdown /r /t 1")
        elif shutdown_mode == "Cut Wi-Fi":
            terminate_network_connection(ask_confirm=False)
        else:
            messagebox.showerror("Invalid Option", "Unknown shutdown type selected.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# def apply_shutdown():
#     selected_type = shutdown_type.get()
#     selected_plan = shutdown_plan.get()

#     confirm = messagebox.askyesno("Confirm", f"Apply plan: {selected_type} → {selected_plan}?\n\nThis will execute immediately.")

#     if confirm:
#         shutdown_system(selected_type)

def open_shutdown_window():
    global shutdown_thread, shutdown_active, remaining, target_time, shutdown_win, cancel_button, target_type, shutdown_target, target_type_dropdown
    global shutdown_window_open, shutdown_win

    if shutdown_window_open and shutdown_win is not None and shutdown_win.winfo_exists():
        shutdown_win.lift()
        return

    shutdown_window_open = True

    shutdown_win = Toplevel()
    shutdown_win.title("System Automation")
    shutdown_win.iconbitmap("Internet_Usage_Monitor.ico")
    shutdown_win.geometry("400x250")
    shutdown_win.resizable(False, False)

    def on_close_shutdown():
        global shutdown_window_open, shutdown_win
        shutdown_window_open = False
        if shutdown_win is not None:
            shutdown_win.destroy()
            shutdown_win = None
        
    shutdown_win.protocol("WM_DELETE_WINDOW", on_close_shutdown)

    target_entry = None
    target_unit = None
    date_entry = None
    time_entry = None
    calendar_dropdown = None
    calendar_type = None
    target_type = None
    
    def schedule_shutdown(target_datetime):
        global remaining, shutdown_thread, shutdown_active, target_time
        global shutdown_window_open
        now = datetime.datetime.now()
        target_time = target_datetime

        if target_time <= now:
            messagebox.showerror("Invalid Time", "Selected time must be in the future.")
            return False

        remaining = (target_time - now).total_seconds()
        shutdown_active = True
        cancel_button.config(state="normal")

        def countdown():
            global remaining, shutdown_active
            global shutdown_window_open, shutdown_win
            while remaining > 0 and shutdown_active:
                time.sleep(1)
                remaining -= 1
            if shutdown_active:
                shutdown_active = False
                try:
                    if shutdown_win is not None and shutdown_win.winfo_exists():
                        shutdown_window_open = False
                        shutdown_win.destroy()
                        shutdown_win = None
                except:
                    pass
                shutdown_system(shutdown_type.get())

        shutdown_thread = threading.Thread(target=countdown, daemon=True)
        shutdown_thread.start()
        return True

    def cancel_shutdown():
        global shutdown_active, remaining, shutdown_targets, shutdown_target
        global shutdown_window_open, shutdown_win
        shutdown_active = False
        remaining = 0
        
        if shutdown_target in shutdown_targets:
            shutdown_targets.remove(shutdown_target)

        shutdown_target = None
        cancel_button.config(state="disabled")
        shutdown_win.destroy()
        shutdown_window_open = False
        shutdown_win = None

    def on_submit():
        global cancel_button
        global shutdown_targets, max_target, downloaded_amount, shutdown_target
        global shutdown_window_open, shutdown_win, selected_shutdown_type

        mode = shutdown_plan.get()
        selected_shutdown_type = shutdown_type.get()
                
        try:
            if mode == "On specific date":
                if not date_entry or not time_entry or not calendar_type:
                    messagebox.showerror("Error", "Date/time inputs are not available.")
                    return
                
                if selected_shutdown_type == "Cut Wi-Fi" and not is_admin():
                    messagebox.showwarning("Administrator Required", "This feature requires administrator privileges. Please run the program as Administrator.")
                    return

                date_str = date_entry.get()
                time_str = time_entry.get()

                if calendar_type.get() == "Solar":
                    j_date = jdatetime.datetime.strptime(date_str + " " + time_str, "%Y/%m/%d %H:%M:%S")
                    g_date = j_date.togregorian()
                    target_datetime = g_date
                else:
                    target_datetime = datetime.datetime.strptime(date_str + " " + time_str, "%Y/%m/%d %H:%M:%S")

                result = schedule_shutdown(target_datetime)
                if result:
                    shutdown_active = True
                    cancel_button.config(state="normal")
                    shutdown_win.destroy()
                    shutdown_win = None
                    shutdown_window_open = False

            elif mode == "On download target":
                if not target_entry or not target_unit:
                    messagebox.showerror("Error", "Download target inputs are not available.")
                    return
                
                if selected_shutdown_type == "Cut Wi-Fi" and not is_admin():
                    messagebox.showwarning("Administrator Required", "This feature requires administrator privileges. Please run the program as Administrator.")
                    return

                try:
                    value = float(target_entry.get())
                    unit = target_unit.get()
                    if unit == "KB":
                        value /= 1024
                    elif unit == "GB":
                        value *= 1024

                    if target_type.get() == "Incremental Download":
                        max_target = downloaded_amount + value
                    else:
                        if value <= downloaded_amount:
                            messagebox.showerror("Invalid Target", f"Target {value:.2f} MB must be greater than already downloaded {downloaded_amount:.2f} MB.")
                            return
                        max_target = value

                    shutdown_target = max_target

                    if shutdown_target not in shutdown_targets:
                        shutdown_targets.append(shutdown_target)

                    shutdown_active = True
                    cancel_button.config(state="normal")
                    # shutdown_win.withdraw()
                    shutdown_win.destroy()
                    shutdown_win = None
                    shutdown_window_open = False 

                    def monitor_download_target():
                        global shutdown_active
                        shutdown_active = True
                        
                        # cancel_button.config(state="normal")
                        try:
                            if cancel_button.winfo_exists():
                                cancel_button.after(0, lambda: cancel_button.config(state="normal"))
                        except:
                            pass
                        # cancel_button.after(0, lambda: cancel_button.config(state="normal"))

                        while shutdown_active:
                            try:
                                if downloaded_amount >= shutdown_target:
                                    shutdown_active = False
                                    try:
                                        if shutdown_win is not None and shutdown_win.winfo_exists():
                                            shutdown_win.destroy()
                                            shutdown_win = None
                                            shutdown_window_open = False
                                    except:
                                        pass
                                    shutdown_system(shutdown_type.get())
                                    break
                                time.sleep(1)
                            except:
                                break

                    threading.Thread(target=monitor_download_target, daemon=True).start()                   

                except ValueError:
                    messagebox.showerror("Invalid Input", "Enter a valid download target value.")

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid date and time in format:\nYYYY/MM/DD and HH:MM:SS")

    def update_ui(*args):
        global shutdown_mode, target_type, target_type_dropdown  
        nonlocal date_entry, time_entry, calendar_dropdown, calendar_type, target_entry, target_unit
        for widget in frame.winfo_children():
            widget.destroy()

        if shutdown_plan.get() == "On specific date":
            shutdown_mode = "date"
            shutdown_win.geometry("400x265")

            tk.Label(frame, text="Date (YYYY/MM/DD):", font=("Segoe UI", 12)).grid(row=0, column=0, padx=5, pady=5)
            date_entry = tk.Entry(frame, width=10, font=("Segoe UI", 12), justify="center")
            date_entry.grid(row=0, column=1, padx=5)

            calendar_type = tk.StringVar(value="Gregorian")
            calendar_dropdown = ttk.Combobox(frame, textvariable=calendar_type, values=["Gregorian", "Solar"], width=11, state="readonly", font=("Segoe UI", 10))
            calendar_dropdown.grid(row=0, column=2, padx=5)

            def update_date_entry(*args):
                now = datetime.datetime.now()
                if calendar_type.get() == "Gregorian":
                    date_entry.delete(0, tk.END)
                    date_entry.insert(0, now.strftime("%Y/%m/%d"))
                else:
                    jalali_date = jdatetime.date.fromgregorian(date=now.date())
                    date_entry.delete(0, tk.END)
                    date_entry.insert(0, jalali_date.strftime("%Y/%m/%d"))

            calendar_dropdown.bind("<<ComboboxSelected>>", update_date_entry)
            update_date_entry()

            tk.Label(frame, text="Time (HH:MM:SS):", font=("Segoe UI", 12)).grid(row=1, column=0, padx=5, pady=5)
            time_entry = tk.Entry(frame, width=10, font=("Segoe UI", 12), justify="center")
            time_entry.insert(0, "00:00:00")
            time_entry.grid(row=1, column=1, padx=5)

            def update_time_entry(option):
                now = datetime.datetime.now()

                if option == "Now":
                    selected_time = now
                elif option == "+30 Minutes":
                    selected_time = now + datetime.timedelta(minutes=30)
                elif option == "+1 Hour":
                    selected_time = now + datetime.timedelta(hours=1)
                elif option == "+1.5 Hours":
                    selected_time = now + datetime.timedelta(hours=1.5)
                elif option == "+2 Hours":
                    selected_time = now + datetime.timedelta(hours=2)
                elif option == "+3 Hours":
                    selected_time = now + datetime.timedelta(hours=3)
                elif option == "+4 Hours":
                    selected_time = now + datetime.timedelta(hours=4)
                elif option == "+5 Hours":
                    selected_time = now + datetime.timedelta(hours=5)
                else:
                    return
                
                formatted_time = selected_time.strftime("%H:%M:%S")
                time_entry.delete(0, tk.END)
                time_entry.insert(0, formatted_time)

            preset_options = ttk.Combobox(frame, width=11, font=("Segoe UI", 10), state="readonly")
            preset_options['values'] = ["Now", "+30 Minutes", "+1 Hour", "+1.5 Hours", "+2 Hours", "+3 Hours", "+4 Hours", "+5 Hours"]
            preset_options.set("Preset Times")
            preset_options.grid(row=1, column=2, padx=5)
            preset_options.bind("<<ComboboxSelected>>", lambda e: update_time_entry(preset_options.get()))

        else:
            shutdown_mode = "download"
            shutdown_win.geometry("400x265")
            tk.Label(frame, text="Target Download:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=5, pady=5)
            target_entry = tk.Entry(frame, width=10, font=("Segoe UI", 12), justify="center")
            target_entry.grid(row=0, column=1, padx=5)
            target_unit = tk.StringVar(value="MB")
            target_dropdown = ttk.Combobox(frame, textvariable=target_unit, values=["KB", "MB", "GB"], width=5, state="readonly", font=("Segoe UI", 10))
            target_dropdown.grid(row=0, column=2, padx=5)
            tk.Label(frame, text="Target Type:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=5, pady=5)
            target_type = tk.StringVar(value="Total Download")
            target_type_dropdown = ttk.Combobox(frame, textvariable=target_type, values=["Total Download", "Incremental Download"], width=20, state="readonly", font=("Segoe UI", 10))
            target_type_dropdown.grid(row=1, column=1, columnspan=2, padx=5)

    tk.Label(shutdown_win, text="Automate Post-Target Action", font=("Segoe UI", 14, "bold")).pack(pady=3)
    tk.Label(shutdown_win, text="Choose Your Plan:", font=("Segoe UI", 12)).pack(pady=3)
   
    combo_frame = tk.Frame(shutdown_win)
    combo_frame.pack(pady=5)

    # tk.Label(combo_frame, text="Trigger:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=(15, 5))
    shutdown_plan = tk.StringVar(value="On specific date")
    plan_dropdown = ttk.Combobox(combo_frame, textvariable=shutdown_plan, values=["On specific date", "On download target"], state="readonly", font=("Segoe UI", 10), width=18)
    plan_dropdown.grid(row=0, column=1, padx=5)
    plan_dropdown.bind("<<ComboboxSelected>>", update_ui)

    # tk.Label(combo_frame, text="Type:", font=("Segoe UI", 10)).grid(row=0, column=2, padx=(0, 5))
    shutdown_type = tk.StringVar(value="Shutdown")
    type_dropdown = ttk.Combobox(combo_frame, textvariable=shutdown_type, values=["Shutdown", "Hibernate", "Sleep", "Restart", "Cut Wi-Fi"], state="readonly", font=("Segoe UI", 10), width=9)
    type_dropdown.grid(row=0, column=3, padx=5)

    frame = tk.Frame(shutdown_win)
    frame.pack(pady=5)

    update_ui()

    button_frame = tk.Frame(shutdown_win)
    button_frame.pack(pady=5)

    shutdown_win.shutdown_icon = ImageTk.PhotoImage(Image.open("shutdown.png"))
    shutdown_button = tk.Button(button_frame, image=shutdown_win.shutdown_icon, command=on_submit, cursor="hand2")
    shutdown_button.pack(side="left", padx=0)

    shutdown_win.cancel_icon = ImageTk.PhotoImage(Image.open("cancel.png"))
    cancel_button = tk.Button(button_frame, image=shutdown_win.cancel_icon, command=cancel_shutdown, cursor="hand2")
    cancel_button.pack(side="left", padx=0)

    if shutdown_active:
        cancel_button.config(state="normal")
    else:
        cancel_button.config(state="disabled")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_wifi_status():
    try:
        result = subprocess.run('netsh interface show interface "Wi-Fi"', capture_output=True, text=True, shell=True)

        if "Connected" in result.stdout:
            return True
        else:
            return False
    except Exception as e:
        messagebox.showerror("Error", f"Error: {str(e)}")
        return False

def terminate_network_connection(ask_confirm=True):
    if not is_admin():
        messagebox.showwarning("Administrator Required", "This feature requires administrator privileges. Please run the program as Administrator.")
        return
    
    is_connected = check_wifi_status()
    if ask_confirm:
        confirm = messagebox.askyesno("Confirm Termination", f"Are you sure you want to {'terminate' if is_connected else 'reconnect'} all network connections? This will execute immediately.")
        if not confirm:
            return
    try:
        if is_connected:
            os.system('netsh interface set interface "Wi-Fi" disable') 
            messagebox.showinfo("Network Connection", "Internet connection has been terminated.")
        else:
            os.system('netsh interface set interface "Wi-Fi" enable')
            messagebox.showinfo("Network Connection", "Internet connection has been restored.")
    except Exception as e:
        messagebox.showerror("Error", f"Error: {str(e)}")

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

usage_image_label = Label(usage_frame, image=usage_icon, bg="#E5E5FF", cursor="hand2")
usage_image_label.pack(side=tk.RIGHT, padx=15, pady=25)
usage_image_label.bind("<Button-1>", lambda event: terminate_network_connection())

usage_label = Label(usage_frame, font=("Segoe UI", 11), bg="#E5E5FF", fg="#333333", anchor="w", justify=tk.LEFT, width=23, height=7)
usage_label.pack(side=tk.RIGHT)

timer_frame = Frame(left_frame, bg="#FBE6FF")
timer_frame.pack(fill=tk.BOTH)

timer_icon = Image.open("timer.png")  
timer_icon = ImageTk.PhotoImage(timer_icon)

timer_image_label = Label(timer_frame, image=timer_icon, bg="#FBE6FF", cursor="hand2")
timer_image_label.pack(side=tk.RIGHT, padx=15, pady=25)
timer_image_label.bind("<Button-1>", lambda event: open_shutdown_window())

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
update_progress()
check_previous_session()
atexit.register(add_end_marker)

# root.attributes('-topmost', True) 

# root.after(100, lambda: unit_var.set("MB"))

root.mainloop()