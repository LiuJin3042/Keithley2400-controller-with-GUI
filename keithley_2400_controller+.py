import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import pyvisa
import threading
import time
import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
5
class Keithley2400Controller:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 2400 Source Meter Controller")
        self.root.geometry("1000x800")
        
        # Instrument connection variables
        self.rm = None
        self.instrument = None
        self.connected = False
        
        # Measurement variables
        self.measuring = False
        self.measurement_thread = None
        self.data = []
        self.start_time = None
        self.save_file_path = None
        self.csv_file = None
        self.csv_writer = None
        
        # Create GUI
        self.create_gui()
        
        # Initialize PyVISA
        self.initialize_visa()
    
    def initialize_visa(self):
        """Initialize PyVISA resource manager"""
        try:
            self.rm = pyvisa.ResourceManager()
            resources = self.rm.list_resources()
            self.resource_combo['values'] = resources
            if resources:
                self.resource_combo.set(resources[0])
        except Exception as e:
            self.log_message(f"Error initializing VISA: {str(e)}")
    
    def create_gui(self):
        """Create the main GUI"""
        # Create main frames
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        plot_frame = ttk.Frame(self.root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Connection frame
        conn_frame = ttk.LabelFrame(control_frame, text="Connection")
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(conn_frame, text="Resource:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.resource_combo = ttk.Combobox(conn_frame, width=30)
        self.resource_combo.grid(row=0, column=1, columnspan=2, padx=5, pady=2)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_instrument)
        self.connect_btn.grid(row=1, column=0, padx=5, pady=5)
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_instrument, state=tk.DISABLED)
        self.disconnect_btn.grid(row=1, column=1, padx=5, pady=5)
        
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=1, column=2, padx=5, pady=5)
        
        # Mode selection frame
        mode_frame = ttk.LabelFrame(control_frame, text="Measurement Mode")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="voltage")
        mode_radio1 = ttk.Radiobutton(mode_frame, text="Source Current, Measure Voltage", 
                                     variable=self.mode_var, value="voltage", 
                                     command=self.update_sequence_labels)
        mode_radio1.pack(anchor=tk.W, padx=5)
        
        mode_radio2 = ttk.Radiobutton(mode_frame, text="Source Voltage, Measure Current", 
                                     variable=self.mode_var, value="current",
                                     command=self.update_sequence_labels)
        mode_radio2.pack(anchor=tk.W, padx=5)
        
        # Sequence input frame
        seq_frame = ttk.LabelFrame(control_frame, text="Measurement Sequence")
        seq_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Auto-generation frame
        auto_frame = ttk.LabelFrame(seq_frame, text="Auto Generate Sequence")
        auto_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # First row: Start and End values
        param_frame1 = ttk.Frame(auto_frame)
        param_frame1.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(param_frame1, text="Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.start_value_entry = ttk.Entry(param_frame1, width=12)
        self.start_value_entry.grid(row=0, column=1, padx=(0, 10))
        self.start_value_entry.insert(0, "0")
        
        ttk.Label(param_frame1, text="End:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.end_value_entry = ttk.Entry(param_frame1, width=12)
        self.end_value_entry.grid(row=0, column=3, padx=(0, 10))
        self.end_value_entry.insert(0, "0.01")
        
        ttk.Label(param_frame1, text="Points:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.num_points_entry = ttk.Entry(param_frame1, width=8)
        self.num_points_entry.grid(row=0, column=5, padx=(0, 10))
        self.num_points_entry.insert(0, "11")
        
        # Second row: Sequence type and generate button
        param_frame2 = ttk.Frame(auto_frame)
        param_frame2.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(param_frame2, text="Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.sequence_type = ttk.Combobox(param_frame2, values=["Linear", "Log (positive)", "Log (negative)"], 
                                        state="readonly", width=15)
        self.sequence_type.grid(row=0, column=1, padx=(0, 10))
        self.sequence_type.set("Linear")
        
        self.generate_btn = ttk.Button(param_frame2, text="Generate Sequence", 
                                     command=self.generate_sequence)
        self.generate_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.clear_sequence_btn = ttk.Button(param_frame2, text="Clear", 
                                           command=self.clear_sequence)
        self.clear_sequence_btn.grid(row=0, column=3)
        
        # Manual input frame
        manual_frame = ttk.LabelFrame(seq_frame, text="Manual Input / Generated Sequence")
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(manual_frame, text="Source Values (one per line):").pack(anchor=tk.W, padx=5)
        self.source_entry = tk.Text(manual_frame, height=6, width=40)
        self.source_entry.pack(padx=5, pady=2)
        self.source_entry.insert(tk.END, "# Enter values manually or use 'Generate Sequence'\n# Example:\n0.001\n0.002\n0.003")
        
        ttk.Label(seq_frame, text="Duration per point (s):").pack(anchor=tk.W, padx=5)
        self.duration_entry = ttk.Entry(seq_frame, width=20)
        self.duration_entry.pack(padx=5, pady=2)
        self.duration_entry.insert(0, "1.0")
        
        ttk.Label(seq_frame, text="Measurement interval (s):").pack(anchor=tk.W, padx=5)
        self.interval_entry = ttk.Entry(seq_frame, width=20)
        self.interval_entry.pack(padx=5, pady=2)
        self.interval_entry.insert(0, "0.1")
        
        # File save settings
        file_frame = ttk.Frame(seq_frame)
        file_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.file_path_var = tk.StringVar()
        ttk.Label(file_frame, text="Save file path:").pack(anchor=tk.W, padx=5)
        
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.file_path_entry = ttk.Entry(path_frame, textvariable=self.file_path_var, width=30)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.browse_btn = ttk.Button(path_frame, text="Browse", command=self.browse_file_path, width=8)
        self.browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.realtime_save_var = tk.BooleanVar(value=True)
        self.realtime_check = ttk.Checkbutton(file_frame, text="Real-time saving (append if file exists)", 
                                            variable=self.realtime_save_var)
        self.realtime_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="Start Measurement", 
                                   command=self.start_measurement, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Measurement", 
                                  command=self.stop_measurement, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear Data", command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(btn_frame, text="Export Data", command=self.export_data)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(control_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=50)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Plot frame
        self.create_plot(plot_frame)
    
    def create_plot(self, parent):
        """Create the plot area"""
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 8))
        self.fig.tight_layout(pad=3.0)
        
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Measured Value')
        self.ax1.set_title('Measurement vs Time')
        self.ax1.grid(True)
        
        self.ax2.set_xlabel('Source Value')
        self.ax2.set_ylabel('Measured Value')
        self.ax2.set_title('I-V Characteristic')
        self.ax2.grid(True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def connect_instrument(self):
        """Connect to the instrument"""
        try:
            resource_name = self.resource_combo.get()
            if not resource_name:
                messagebox.showerror("Error", "Please select a resource")
                return
            
            self.instrument = self.rm.open_resource(resource_name)
            self.instrument.timeout = 5000  # 5 second timeout
            
            # Test connection
            idn = self.instrument.query("*IDN?").strip()
            self.log_message(f"Connected to: {idn}")
            
            # Initialize instrument
            self.instrument.write("*RST")  # Reset instrument
            time.sleep(1)  # Wait for reset to complete
            self.instrument.write("*CLS")  # Clear status
            self.instrument.write("SOUR:FUNC VOLT")  # Default to voltage source
            self.instrument.write("SENS:FUNC 'CURR'")  # Default to current measurement
            self.instrument.write("SENS:CURR:PROT 0.1")  # Set current compliance to 100mA
            self.instrument.write("SENS:VOLT:PROT 20")  # Set voltage compliance to 20V
            self.instrument.write("OUTP ON")  # Turn output on
            
            self.connected = True
            self.status_label.config(text="Status: Connected", foreground="green")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.log_message(f"Connection failed: {str(e)}")
    
    def generate_sequence(self):
        """Generate voltage/current sequence based on user parameters"""
        try:
            # Get parameters
            start_val = float(self.start_value_entry.get())
            end_val = float(self.end_value_entry.get())
            num_points = int(self.num_points_entry.get())
            seq_type = self.sequence_type.get()
            
            # Validate inputs
            if num_points < 2:
                messagebox.showerror("Error", "Number of points must be at least 2")
                return
            
            # Generate sequence based on type
            if seq_type == "Linear":
                values = np.linspace(start_val, end_val, num_points)
            elif seq_type == "Log (positive)":
                if start_val <= 0 or end_val <= 0:
                    messagebox.showerror("Error", "For logarithmic sequence, both start and end values must be positive")
                    return
                values = np.logspace(np.log10(abs(start_val)), np.log10(abs(end_val)), num_points)
                if start_val < 0:  # If original start was negative, make all values negative
                    values = -values
            elif seq_type == "Log (negative)":
                if start_val >= 0 or end_val >= 0:
                    messagebox.showerror("Error", "For negative logarithmic sequence, both start and end values must be negative")
                    return
                # Work with absolute values for log calculation, then make negative
                abs_start = abs(start_val)
                abs_end = abs(end_val)
                if abs_start < abs_end:  # More negative to less negative
                    values = -np.logspace(np.log10(abs_start), np.log10(abs_end), num_points)
                else:  # Less negative to more negative
                    values = -np.logspace(np.log10(abs_end), np.log10(abs_start), num_points)[::-1]
            
            # Format values and insert into text box
            self.clear_sequence()  # Clear existing content
            
            # Add header comment
            mode = self.mode_var.get()
            unit = "A" if mode == "voltage" else "V"
            header = f"# Generated {seq_type} sequence: {start_val} to {end_val} {unit} ({num_points} points)\n"
            
            # Add values
            value_lines = "\n".join([f"{val:.6g}" for val in values])
            
            self.source_entry.insert(tk.END, header + value_lines)
            
            # Log the generation
            self.log_message(f"Generated {seq_type} sequence: {num_points} points from {start_val} to {end_val}")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input values: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sequence: {str(e)}")
    
    def clear_sequence(self):
        """Clear the sequence input box"""
        self.source_entry.delete(1.0, tk.END)
    
    def update_sequence_labels(self):
        """Update labels based on current measurement mode"""
        mode = self.mode_var.get()
        if hasattr(self, 'start_value_entry'):  # Check if auto-generation widgets exist
            if mode == "voltage":
                unit_text = "(A)"
            else:
                unit_text = "(V)"
            
            # Update the example in the manual input box if it's still showing the default
            current_text = self.source_entry.get(1.0, tk.END).strip()
            if "Enter values manually" in current_text or "Example:" in current_text:
                self.clear_sequence()
                if mode == "voltage":
                    default_text = "# Enter current values manually or use 'Generate Sequence'\n# Example (Amperes):\n0.001\n0.002\n0.003"
                else:
                    default_text = "# Enter voltage values manually or use 'Generate Sequence'\n# Example (Volts):\n0.1\n0.2\n0.3"
                self.source_entry.insert(tk.END, default_text)
    
    def browse_file_path(self):
        """Browse and select file path for saving data"""
        file_path = filedialog.asksaveasfilename(
            title="Select file to save measurement data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"keithley_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def setup_realtime_save(self, mode):
        """Setup real-time CSV file writing"""
        if not self.realtime_save_var.get():
            return True
        
        file_path = self.file_path_var.get().strip()
        if not file_path:
            messagebox.showerror("Error", "Please specify a file path for real-time saving")
            return False
        
        try:
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists(file_path)
            
            # Open file in append mode
            self.csv_file = open(file_path, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write headers only if file is new or empty
            if not file_exists or os.path.getsize(file_path) == 0:
                if mode == "voltage":
                    headers = ['Timestamp', 'Time (s)', 'Current (A)', 'Voltage (V)', 'Mode']
                else:
                    headers = ['Timestamp', 'Time (s)', 'Voltage (V)', 'Current (A)', 'Mode']
                
                self.csv_writer.writerow(headers)
                self.csv_file.flush()
                self.log_message(f"Created new file: {file_path}")
            else:
                self.log_message(f"Appending to existing file: {file_path}")
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to setup file for saving: {str(e)}")
            return False
    
    def close_realtime_save(self):
        """Close real-time CSV file"""
        try:
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
        except Exception as e:
            self.log_message(f"Error closing file: {str(e)}")
    
    def write_data_realtime(self, elapsed_time, source_val, measured_val, mode):
        """Write data point to file in real-time"""
        if not self.realtime_save_var.get() or not self.csv_writer:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Include milliseconds
            mode_str = "I->V" if mode == "voltage" else "V->I"
            
            row = [timestamp, elapsed_time, source_val, measured_val, mode_str]
            self.csv_writer.writerow(row)
            self.csv_file.flush()  # Ensure data is written immediately
            
        except Exception as e:
            self.log_message(f"Error writing to file: {str(e)}")

    def disconnect_instrument(self):
        """Disconnect from the instrument"""
        try:
            if self.instrument:
                self.instrument.write("OUTP OFF")  # Turn output off
                self.instrument.close()
            self.connected = False
            self.status_label.config(text="Status: Disconnected", foreground="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.DISABLED)
            self.log_message("Disconnected from instrument")
        except Exception as e:
            self.log_message(f"Disconnect error: {str(e)}")
    
    def parse_source_values(self):
        """Parse source values from text input"""
        text = self.source_entry.get(1.0, tk.END).strip()
        values = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    values.append(float(line))
                except ValueError:
                    continue
        return values
    
    def start_measurement(self):
        """Start the measurement sequence"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to instrument")
            return
        
        try:
            source_values = self.parse_source_values()
            if not source_values:
                messagebox.showerror("Error", "No valid source values entered")
                return
            
            duration = float(self.duration_entry.get())
            interval = float(self.interval_entry.get())
            
            if duration <= 0 or interval <= 0:
                messagebox.showerror("Error", "Duration and interval must be positive")
                return
            
            # Setup real-time saving
            mode = self.mode_var.get()
            if not self.setup_realtime_save(mode):
                return
            
            self.measuring = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.data = []
            self.start_time = time.time()
            
            # Configure instrument based on mode
            if mode == "voltage":
                self.instrument.write("SOUR:FUNC CURR")
                self.instrument.write("SENS:FUNC 'VOLT'")
                self.instrument.write("SENS:VOLT:PROT 20")  # Set voltage compliance
                self.instrument.write("OUTP ON")  # Turn output on
                self.log_message("Mode: Source Current, Measure Voltage")
            else:
                self.instrument.write("SOUR:FUNC VOLT")
                self.instrument.write("SENS:FUNC 'CURR'")
                self.instrument.write("SENS:CURR:PROT 0.1")  # Set current compliance
                self.instrument.write("OUTP ON")  # Turn output on
                self.log_message("Mode: Source Voltage, Measure Current")
            
            # Start measurement thread
            self.measurement_thread = threading.Thread(
                target=self.measurement_worker,
                args=(source_values, duration, interval, mode)
            )
            self.measurement_thread.daemon = True
            self.measurement_thread.start()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start measurement: {str(e)}")
    
    def measurement_worker(self, source_values, duration, interval, mode):
        """Worker thread for measurements"""
        try:
            for i, source_val in enumerate(source_values):
                if not self.measuring:
                    break
                
                # Set source value
                if mode == "voltage":
                    self.instrument.write(f"SOUR:CURR {source_val}")
                else:
                    self.instrument.write(f"SOUR:VOLT {source_val}")
                self.log_message(f"Point {i+1}/{len(source_values)}: Source = {source_val}")
                
                # Measure for specified duration
                point_start = time.time()
                while (time.time() - point_start) < duration and self.measuring:
                    try:
                        # Read measurement
                        measurement = self.instrument.query("READ?").strip()
                        values = [float(x) for x in measurement.split(',')]
                        
                        elapsed_time = time.time() - self.start_time
                        
                        if mode == "voltage":
                            measured_val = values[0]  # Voltage reading
                            self.data.append((elapsed_time, source_val, measured_val, "V"))
                            # Write to file in real-time
                            self.write_data_realtime(elapsed_time, source_val, measured_val, mode)
                        else:
                            measured_val = values[1]  # Current reading  
                            self.data.append((elapsed_time, source_val, measured_val, "A"))
                            # Write to file in real-time
                            self.write_data_realtime(elapsed_time, source_val, measured_val, mode)
                        
                        # Update plot in main thread
                        self.root.after(0, self.update_plot)
                        
                    except Exception as e:
                        self.log_message(f"Measurement error: {str(e)}")
                    
                    time.sleep(interval)
            
            # Measurement complete
            self.root.after(0, self.measurement_complete)
            
        except Exception as e:
            self.log_message(f"Measurement thread error: {str(e)}")
            self.root.after(0, self.measurement_complete)
    
    def update_plot(self):
        """Update the plots with current data"""
        if not self.data:
            return
        
        times = [d[0] for d in self.data]
        source_vals = [d[1] for d in self.data]
        measured_vals = [d[2] for d in self.data]
        
        # Clear and update time plot
        self.ax1.clear()
        self.ax1.plot(times, measured_vals, 'b.-', markersize=3)
        self.ax1.set_xlabel('Time (s)')
        
        mode = self.mode_var.get()
        if mode == "voltage":
            self.ax1.set_ylabel('Voltage (V)')
            self.ax1.set_title('Voltage vs Time')
        else:
            self.ax1.set_ylabel('Current (A)')
            self.ax1.set_title('Current vs Time')
        
        self.ax1.grid(True)
        
        # Clear and update I-V plot
        self.ax2.clear()
        self.ax2.plot(source_vals, measured_vals, 'r.-', markersize=3)
        
        if mode == "voltage":
            self.ax2.set_xlabel('Current (A)')
            self.ax2.set_ylabel('Voltage (V)')
            self.ax2.set_title('I-V Characteristic')
        else:
            self.ax2.set_xlabel('Voltage (V)')
            self.ax2.set_ylabel('Current (A)')
            self.ax2.set_title('V-I Characteristic')
        
        self.ax2.grid(True)
        
        self.canvas.draw()
    
    def stop_measurement(self):
        """Stop the current measurement"""
        self.measuring = False
        # Close real-time save file
        self.close_realtime_save()
        self.measurement_complete()
    
    def measurement_complete(self):
        """Called when measurement is complete"""
        self.measuring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # Close real-time save file
        self.close_realtime_save()
        self.log_message("Measurement completed")
    
    def clear_data(self):
        """Clear all data and plots"""
        self.data = []
        self.ax1.clear()
        self.ax2.clear()
        
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Measured Value')
        self.ax1.set_title('Measurement vs Time')
        self.ax1.grid(True)
        
        self.ax2.set_xlabel('Source Value')
        self.ax2.set_ylabel('Measured Value')
        self.ax2.set_title('I-V Characteristic')
        self.ax2.grid(True)
        
        self.canvas.draw()
        self.log_message("Data cleared")
    
    def export_data(self):
        """Export current data to a new CSV file"""
        if not self.data:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                title="Export measurement data",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"keithley_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not file_path:
                return
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                mode = self.mode_var.get()
                
                if mode == "voltage":
                    writer.writerow(['Time (s)', 'Current (A)', 'Voltage (V)'])
                else:
                    writer.writerow(['Time (s)', 'Voltage (V)', 'Current (A)'])
                
                for row in self.data:
                    writer.writerow([row[0], row[1], row[2]])
            
            self.log_message(f"Data exported to {file_path}")
            messagebox.showinfo("Success", f"Data exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        # Close any open CSV file
        self.close_realtime_save()
        
        if self.connected and self.instrument:
            try:
                self.instrument.write("OUTP OFF")
                self.instrument.close()
            except:
                pass

def main():
    root = tk.Tk()
    app = Keithley2400Controller(root)
    
    def on_closing():
        if app.measuring:
            app.stop_measurement()
        if app.connected:
            app.disconnect_instrument()
        # Ensure CSV file is closed
        app.close_realtime_save()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()