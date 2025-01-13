import psutil
import pystray
from PIL import Image, ImageDraw
import time
import threading
import sys
import tkinter as tk
import queue

class NetworkMonitor:
    def __init__(self):
        # Core components
        self.running = True
        self.shutting_down = False
        self.update_queue = queue.Queue()
        self.monitor_thread = None
        self.icon_thread = None
        
        # Network stats
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.speed_sent = 0
        self.speed_recv = 0
        self.last_update = time.time()
        
        # Window state
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Settings
        self.position_x = 100
        self.position_y = 100
        
        # GUI components
        self.root = None
        self.icon = None
        
        # Initialize
        self.setup_gui()
        print("Network Monitor started")

    def setup_gui(self):
        """Setup main GUI window"""
        self.root = tk.Tk()
        self.root.title("Network Monitor")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Main frame
        self.main_frame = tk.Frame(self.root, bg="#90EE90")
        self.main_frame.pack(fill="both", expand=True)
        
        # Content frame
        content_frame = tk.Frame(self.main_frame, bg="#90EE90")
        content_frame.pack(side="left", padx=2)
        
        # Upload speed
        self.upload_arrow = tk.Label(
            content_frame,
            text="↑",
            font=("Arial", 10),
            fg="#000000",
            bg="#90EE90"
        )
        self.upload_arrow.pack(side="left", padx=(0, 1))
        
        self.upload_label = tk.Label(
            content_frame,
            text="0 KB/s",
            font=("Arial", 10),
            fg="#000000",
            bg="#90EE90"
        )
        self.upload_label.pack(side="left", padx=(0, 5))
        
        # Download speed
        self.download_arrow = tk.Label(
            content_frame,
            text="↓",
            font=("Arial", 10),
            fg="#000000",
            bg="#90EE90"
        )
        self.download_arrow.pack(side="left", padx=(0, 1))
        
        self.download_label = tk.Label(
            content_frame,
            text="0 KB/s",
            font=("Arial", 10),
            fg="#000000",
            bg="#90EE90"
        )
        self.download_label.pack(side="left")
        
        # Window setup
        self.root.geometry(f"180x22+{self.position_x}+{self.position_y}")
        
        # Bind events
        for widget in [self.root, self.main_frame, content_frame, 
                      self.upload_arrow, self.upload_label,
                      self.download_arrow, self.download_label]:
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.on_drag)
            widget.bind('<ButtonRelease-1>', self.stop_drag)
            widget.bind('<Button-3>', self.show_popup_menu)
        
        # Create popup menu
        self.setup_menu()
        
        # Keep on top
        self.root.after(100, self.keep_on_top)
        
        # Bind GUI updates
        self.root.bind('<<UpdateGUI>>', self._handle_gui_update)

    def setup_menu(self):
        """Create right-click menu"""
        self.popup_menu = tk.Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="Hide to Tray", command=lambda: self.minimize_to_tray())
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Exit", command=lambda: self.root.after(0, self.on_exit))

    def update_network_stats(self):
        """Update network statistics"""
        while self.running and not self.shutting_down:
            try:
                current_time = time.time()
                if current_time - self.last_update < 1.0:  # Update every second
                    time.sleep(0.1)
                    continue

                # Get network stats
                stats = psutil.net_io_counters()
                new_bytes_sent = stats.bytes_sent
                new_bytes_recv = stats.bytes_recv

                # Calculate speeds
                time_diff = current_time - self.last_update
                self.speed_sent = (new_bytes_sent - self.bytes_sent) / time_diff
                self.speed_recv = (new_bytes_recv - self.bytes_recv) / time_diff
                
                self.bytes_sent = new_bytes_sent
                self.bytes_recv = new_bytes_recv
                self.last_update = current_time

                # Update GUI
                if not self.shutting_down:
                    self.update_gui()

                # Update tray tooltip
                if self.icon and not self.shutting_down:
                    up = self.format_speed(self.speed_sent)
                    down = self.format_speed(self.speed_recv)
                    self.icon.title = f"↑ {up}/s\n↓ {down}/s"

            except Exception as e:
                if not self.shutting_down:
                    print(f"Error updating stats: {e}")
                time.sleep(1)

    def update_gui(self):
        """Update GUI with current speeds"""
        if not self.running or self.shutting_down:
            return
            
        try:
            if self.root and self.root.winfo_exists():
                self.update_queue.put((self.speed_sent, self.speed_recv))
                self.root.event_generate('<<UpdateGUI>>')
        except:
            pass

    def _handle_gui_update(self, event):
        """Handle GUI updates"""
        if self.shutting_down:
            return
            
        try:
            while not self.update_queue.empty():
                speed_sent, speed_recv = self.update_queue.get_nowait()
                
                if self.root and self.root.winfo_exists():
                    self.upload_label.configure(text=self.format_speed_compact(speed_sent))
                    self.download_label.configure(text=self.format_speed_compact(speed_recv))
                    
                self.update_queue.task_done()
        except:
            pass

    def format_speed(self, bytes_per_sec):
        """Format speed with units"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_per_sec < 1024:
                return f"{bytes_per_sec:.1f} {unit}"
            bytes_per_sec /= 1024
        return f"{bytes_per_sec:.1f} TB"
    
    def format_speed_compact(self, bytes_per_sec):
        """Format speed in compact form"""
        bytes_per_sec /= 1024  # Convert to KB
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.1f} KB/s"
        bytes_per_sec /= 1024
        return f"{bytes_per_sec:.1f} MB/s"

    def start_drag(self, event):
        """Start window drag"""
        self.dragging = True
        self.drag_start_x = event.x_root - self.root.winfo_x()
        self.drag_start_y = event.y_root - self.root.winfo_y()
        
    def on_drag(self, event):
        """Handle window drag"""
        if self.dragging:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")
            
    def stop_drag(self, event):
        """Stop window drag"""
        self.dragging = False
        self.position_x = self.root.winfo_x()
        self.position_y = self.root.winfo_y()

    def show_popup_menu(self, event):
        """Show right-click menu"""
        if self.shutting_down or not self.root or not self.root.winfo_exists():
            return
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        except:
            pass
        finally:
            try:
                self.popup_menu.grab_release()
            except:
                pass

    def create_icon(self):
        """Create system tray icon"""
        image = Image.new('RGBA', (32, 32), color=(0,0,0,0))
        dc = ImageDraw.Draw(image)
        dc.ellipse([0, 0, 31, 31], fill="#90EE90")
        dc.rectangle([6, 14, 26, 18], fill="#000000")
        dc.rectangle([14, 6, 18, 26], fill="#000000")
        return image

    def setup_tray_icon(self):
        """Setup system tray icon"""
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Exit", self.on_tray_exit)
            )
            
            self.icon = pystray.Icon(
                "Network Monitor",
                self.create_icon(),
                "Network Traffic Monitor",
                menu=menu
            )
            
            self.icon_thread = threading.Thread(target=self.icon.run)
            self.icon_thread.daemon = True
            self.icon_thread.start()
        except Exception as e:
            print(f"Error setting up tray icon: {e}")

    def minimize_to_tray(self):
        """Hide window to system tray"""
        if self.root:
            self.root.withdraw()
            
    def show_window(self, icon=None):
        """Show window from tray"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.geometry(f"+{self.position_x}+{self.position_y}")

    def keep_on_top(self):
        """Keep window on top"""
        if self.shutting_down or not self.root or not self.root.winfo_exists():
            return
        try:
            if not self.shutting_down:
                self.root.lift()
                self.root.attributes('-topmost', True)
                if not self.shutting_down:
                    self.root.after(100, self.keep_on_top)
        except:
            pass

    def cleanup(self):
        """Clean up resources"""
        if self.shutting_down:
            return
            
        self.shutting_down = True
        self.running = False
        
        # Cancel all pending after callbacks
        if self.root and self.root.winfo_exists():
            try:
                for after_id in self.root.tk.call('after', 'info'):
                    self.root.after_cancel(after_id)
            except:
                pass
        
        # Clear queue
        while not self.update_queue.empty():
            try:
                self.update_queue.get_nowait()
                self.update_queue.task_done()
            except:
                pass

        # Stop icon first
        if self.icon:
            try:
                self.icon.stop()
            except:
                pass

        # Destroy window
        if self.root and self.root.winfo_exists():
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass

        # Wait for threads
        try:
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            if self.icon_thread and self.icon_thread.is_alive():
                self.icon_thread.join(timeout=1.0)
        except:
            pass
                
        # Clear references
        self.root = None
        self.icon = None

    def on_exit(self):
        """Exit application"""
        if self.shutting_down:
            return
        self.cleanup()
        sys.exit(0)
        
    def on_tray_exit(self, icon, item):
        """Exit from tray icon"""
        if self.shutting_down:
            return
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Run the application"""
        try:
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self.update_network_stats)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # Setup tray icon
            self.setup_tray_icon()
            
            # Run main loop
            if self.root:
                self.root.protocol("WM_DELETE_WINDOW", self.on_exit)  # Handle window close button
                self.root.mainloop()
                
        except Exception as e:
            print(f"Error running Network Monitor: {e}")
            self.cleanup()
            sys.exit(1)

if __name__ == "__main__":
    try:
        monitor = NetworkMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        if monitor:
            monitor.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if monitor:
            monitor.cleanup()
        sys.exit(1) 