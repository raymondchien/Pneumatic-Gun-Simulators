import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, ScalarFormatter
from scipy.integrate import solve_ivp
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import pickle
from pathlib import Path

MM_PER_METER = 1000.0
GRAMS_PER_KG = 1000.0
FPS_PER_MPS = 3.280839895013123
BAR_PER_PASCAL = 1e-5
ML_PER_M3 = 1_000_000.0
MS_PER_S = 1000.0

class DartPlungerSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Spring Plunger Simulator")
        self._configure_window()
        
        # Default parameters
        self.params = {
            'p_0': 101325,          # Initial pressure inside plunger tube (Pa)
            'p_2': 101325,          # Ambient pressure (Pa)
            'D_b': 0.0127,          # Diameter of barrel (m)
            'D_p': 0.035052,        # Diameter of plunger (m)
            'gamma': 1.4,           # Adiabatic index cp/cv for air
            'mass_d': 0.0012,       # Mass of dart (kg)
            'mass_p': 0.06,         # Mass of plunger (kg)
            'fric1': 0.4,           # Static friction force (N)
            'fric2': 0.2,           # Dynamic friction term (N)
            'xso': 0.0254,          # Spring compression before priming (m)
            'L_0': 0.1016,          # Initial plunger length (m)
            'k': 523 * (11/5),      # Spring constant (N/m)
            'end_time': 0.02,       # Simulation end time (s)
            'n_points': 1500        # Number of evaluation points
        }
        self.display_converters = {
            'p_0': (lambda v: v * BAR_PER_PASCAL, lambda v: v / BAR_PER_PASCAL),
            'p_2': (lambda v: v * BAR_PER_PASCAL, lambda v: v / BAR_PER_PASCAL),
            'D_b': (lambda v: v * MM_PER_METER, lambda v: v / MM_PER_METER),
            'D_p': (lambda v: v * MM_PER_METER, lambda v: v / MM_PER_METER),
            'mass_d': (lambda v: v * GRAMS_PER_KG, lambda v: v / GRAMS_PER_KG),
            'mass_p': (lambda v: v * GRAMS_PER_KG, lambda v: v / GRAMS_PER_KG),
            'xso': (lambda v: v * MM_PER_METER, lambda v: v / MM_PER_METER),
            'L_0': (lambda v: v * MM_PER_METER, lambda v: v / MM_PER_METER),
            'end_time': (lambda v: v * MS_PER_S, lambda v: v / MS_PER_S),
        }
        self.current_param_file = None
        
        self.setup_gui()
        self.run_simulation()  # Initial simulation

    def _configure_window(self):
        """Try to maximize the window cross-platform; fall back to full-screen geometry."""
        self.root.update_idletasks()

        try:
            self.root.state('zoomed')  # Windows (and some *nix)
            return
        except tk.TclError:
            pass

        try:
            self.root.attributes('-zoomed', True)  # Some Linux window managers
            return
        except tk.TclError:
            pass

        # Mac and other environments: manually size and anchor top-left
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
    def setup_gui(self):
        # Create main frames with very generous spacing
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for controls - compact but readable
        control_frame = ttk.Frame(main_container, width=350)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        control_frame.pack_propagate(False)  # Maintain fixed width
        
        # Right panel for plots - takes up most space
        plot_frame = ttk.Frame(main_container)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Setup control panel
        self.setup_controls(control_frame)
        
        # Setup plot area with maximum space
        self.create_plots(plot_frame)
        
    def setup_controls(self, parent):
        # Title
        title_label = ttk.Label(parent, text="Dart-Plunger Simulator", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # Create parameter frame (no scrolling needed)
        params_container = ttk.Frame(parent)
        params_container.pack(fill=tk.X, expand=False)
        
        # Parameter definitions
        param_info = {
            'p_0': ('Initial Pressure (bar)', 0.5, 2.0),
            'p_2': ('Ambient Pressure (bar)', 0.5, 2.0),
            'D_b': ('Barrel Diameter (mm)', 5, 20),
            'D_p': ('Plunger Diameter (mm)', 20, 50),
            'gamma': ('Adiabatic Index', 1.0, 2.0),
            'mass_d': ('Dart Mass (g)', 0.5, 5),
            'mass_p': ('Plunger Mass (g)', 10, 200),
            'fric1': ('Static Friction (N)', 0, 2),
            'fric2': ('Dynamic Friction (N)', 0, 1),
            'xso': ('Spring Precompression (mm)', 10, 50),
            'L_0': ('Initial Plunger Length (mm)', 50, 200),
            'k': ('Spring Constant (N/m)', 100, 2000),
            'end_time': ('End Time (ms)', 5, 100),
            'n_points': ('Number of Points', 500, 3000)
        }
        
        self.param_vars = {}
        
        for key, (label, min_val, max_val) in param_info.items():
            param_frame = ttk.Frame(params_container)
            param_frame.pack(fill=tk.X, pady=3)
            
            # Label with fixed width
            ttk.Label(param_frame, text=label, width=22).pack(side=tk.LEFT)
            
            # Entry with larger font for readability
            display_value = self._param_to_display(key, self.params[key])
            var = tk.DoubleVar(value=display_value)
            self.param_vars[key] = var
            
            entry = ttk.Entry(param_frame, textvariable=var, width=12, font=('Arial', 10))
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<Return>', lambda e: self.run_simulation_threaded())
        
        # Action buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10, fill=tk.X)
        
        load_button = ttk.Button(button_frame, text="Load", command=self.load_parameters)
        load_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        save_button = ttk.Button(button_frame, text="Save", command=self.save_parameters)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        run_button = ttk.Button(button_frame, text="Run Simulation", 
                               command=self.run_simulation_threaded)
        run_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        self.file_label = ttk.Label(parent, text="No parameter file selected")
        self.file_label.pack(fill=tk.X, pady=(0, 10))
        
        # Results display
        results_label = ttk.Label(parent, text="Results Summary:", font=('Arial', 12, 'bold'))
        results_label.pack(pady=(20, 5))
        
        results_container = ttk.Frame(parent)
        results_container.pack(fill=tk.BOTH, expand=True, pady=5)

        self.results_text = scrolledtext.ScrolledText(results_container, width=40, 
                                                     font=('Courier', 9))
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Status
        self.status_label = ttk.Label(parent, text="Ready", foreground="green", 
                                     font=('Arial', 10))
        self.status_label.pack(pady=10)
        
    def create_plots(self, parent):
        # Create very large matplotlib figure for maximum readability
        self.fig = Figure(figsize=(18, 12), dpi=100)
        
        # Create 3x3 subplot layout with generous spacing
        self.axes = []
        for i in range(9):
            ax = self.fig.add_subplot(3, 3, i+1)
            self.axes.append(ax)
        
        # Adjust subplot parameters for maximum readability
        self.fig.subplots_adjust(
            left=0.08,      # Left margin
            bottom=0.07,    # Bottom margin  
            right=0.97,     # Right margin
            top=0.93,       # Top margin
            wspace=0.35,    # Width spacing between subplots
            hspace=0.45     # Height spacing between subplots
        )
        
        # Embed in tkinter with scrollbars if needed
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add navigation toolbar (with error handling)
        toolbar_frame = tk.Frame(canvas_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            nav_toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            nav_toolbar.update()
        except Exception as e:
            print(f"Navigation toolbar not available: {e}")
        
    def system(self, t, x):
        """Define the system of first-order ODEs"""
        d1, d2, p1, p2 = x  # dart and plunger variables
        
        # Calculate areas
        area_b = np.pi * (self.params['D_b']**2) / 4
        area_p = np.pi * (self.params['D_p']**2) / 4
        v_0 = self.params['L_0'] * area_p
        xsf = self.params['xso'] + self.params['L_0']
        
        # Internal pressure calculation (with safety checks)
        volume_ratio = np.maximum(
            ((self.params['L_0'] - p1) * area_p + d1 * area_b) / v_0,
            1e-10  # Prevent division by zero
        )
        p_t = self.params['p_0'] / (volume_ratio ** self.params['gamma'])
        
        # Derivatives
        dd1dt = d2  # dart velocity
        dp1dt = p2  # plunger velocity
        
        # Accelerations
        dp2dt = ((self.params['p_2'] - p_t) * area_p + 
                self.params['k'] * (xsf - p1)) / self.params['mass_p']
        dd2dt = ((p_t - self.params['p_2']) * area_b) / self.params['mass_d']
        
        return [dd1dt, dd2dt, dp1dt, dp2dt]
        
    def run_simulation(self):
        try:
            # Update parameters
            self._update_params_from_vars()
            
            # Solve ODE
            x0 = [0, 0, 0, 0]
            t_span = (0, self.params['end_time'])
            t_eval = np.linspace(0, self.params['end_time'], int(self.params['n_points']))
            
            sol = solve_ivp(self.system, t_span, x0, t_eval=t_eval)
            
            if not sol.success:
                raise Exception("ODE solver failed")
            
            # Extract results
            d1_pos, d1_vel, p1_pos, p1_vel = sol.y
            time_ms = sol.t * MS_PER_S
            
            # Calculate derived quantities
            area_b = np.pi * (self.params['D_b']**2) / 4
            area_p = np.pi * (self.params['D_p']**2) / 4
            v_0 = self.params['L_0'] * area_p
            xsf = self.params['xso'] + self.params['L_0']
            
            # Avoid division by zero or negative values
            volume_ratio = np.maximum(
                ((self.params['L_0'] - p1_pos) * area_p + d1_pos * area_b) / v_0,
                1e-10
            )
            p_t_array = self.params['p_0'] / (volume_ratio ** self.params['gamma'])
            v_t_array = (self.params['L_0'] - p1_pos) * area_p + area_b * d1_pos
            spring_force = self.params['k'] * (xsf - p1_pos)

            # Prepare data in display units
            d1_pos_mm = d1_pos * MM_PER_METER
            d1_vel_fps = d1_vel * FPS_PER_MPS
            p1_pos_mm = p1_pos * MM_PER_METER
            p1_vel_fps = p1_vel * FPS_PER_MPS
            p_t_bar = p_t_array * BAR_PER_PASCAL
            v_t_ml = v_t_array * ML_PER_M3
            
            # Clear and plot with large, readable formatting
            for ax in self.axes:
                ax.clear()
            
            # Configure all axes for maximum readability
            plot_configs = [
                (time_ms, d1_pos_mm, 'Dart Position vs Time', 'Time (ms)', 'Position (mm)', 'blue', True),
                (time_ms, d1_vel_fps, 'Dart Velocity vs Time', 'Time (ms)', 'Velocity (fps)', 'red', True),
                (d1_pos_mm, d1_vel_fps, 'Dart Velocity vs Dart Position', 'Dart Position (mm)', 'Velocity (fps)', 'purple', False),
                (time_ms, p1_pos_mm, 'Plunger Position vs Time', 'Time (ms)', 'Position (mm)', 'green', True),
                (time_ms, p1_vel_fps, 'Plunger Velocity vs Time', 'Time (ms)', 'Velocity (fps)', 'magenta', True),
                (d1_pos_mm, p1_pos_mm, 'Plunger Position vs Dart Position', 'Dart Position (mm)', 'Plunger Position (mm)', 'brown', False),
                (time_ms, p_t_bar, 'System Pressure vs Time', 'Time (ms)', 'Pressure (bar)', 'cyan', True),
                (time_ms, v_t_ml, 'System Volume vs Time', 'Time (ms)', 'Volume (mL)', 'orange', True),
                (d1_pos_mm, p_t_bar, 'Pressure vs Dart Position', 'Dart Position (mm)', 'Pressure (bar)', 'teal', False),
            ]
            
            for i, (x_data, y_data, title, xlabel, ylabel, color, use_time_xlim) in enumerate(plot_configs):
                ax = self.axes[i]
                ax.plot(x_data, y_data, color=color, linewidth=3)
                ax.set_xlabel(xlabel, fontsize=12)
                ax.set_ylabel(ylabel, fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', labelsize=11)
                ax.tick_params(axis='x', labelrotation=0)
                if use_time_xlim:
                    ax.set_xlim(left=0, right=self.params['end_time'] * MS_PER_S)
                else:
                    x_min = np.nanmin(x_data)
                    x_max = np.nanmax(x_data)
                    if np.isfinite(x_min) and np.isfinite(x_max):
                        if x_min == x_max:
                            span = abs(x_min) * 0.05 or 1.0
                            ax.set_xlim(x_min - span, x_max + span)
                        else:
                            ax.set_xlim(x_min, x_max)
                if np.nanmin(y_data) >= 0:
                    ax.set_ylim(bottom=0)
                ax.set_title(title, fontsize=14, fontweight='bold')

                # Keep both axes in plain notation
                x_formatter = ScalarFormatter(useMathText=False)
                x_formatter.set_scientific(False)
                x_formatter.set_useOffset(False)
                ax.xaxis.set_major_formatter(x_formatter)

                y_formatter = ScalarFormatter(useMathText=False)
                y_formatter.set_scientific(False)
                y_formatter.set_useOffset(False)
                ax.yaxis.set_major_formatter(y_formatter)
                ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
            
            self.canvas.draw()
            
            # Update results summary
            self.update_results_summary(sol, d1_pos, d1_vel, p1_pos, p1_vel, p_t_array, v_t_array)
            
            self.status_label.config(text="Simulation completed successfully", 
                                   foreground="green")
            
        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed: {str(e)}")
            self.status_label.config(text="Simulation failed", foreground="red")
    
    def update_results_summary(self, sol, d1_pos, d1_vel, p1_pos, p1_vel, p_t_array, v_t_array):
        """Update the results text widget"""
        final_dart_pos_mm = d1_pos[-1] * MM_PER_METER
        final_dart_vel_fps = d1_vel[-1] * FPS_PER_MPS
        max_dart_vel_fps = np.max(d1_vel) * FPS_PER_MPS

        final_plunger_pos_mm = p1_pos[-1] * MM_PER_METER
        final_plunger_vel_fps = p1_vel[-1] * FPS_PER_MPS
        max_plunger_vel_fps = np.max(np.abs(p1_vel)) * FPS_PER_MPS

        final_pressure_bar = p_t_array[-1] * BAR_PER_PASCAL
        min_pressure_bar = np.min(p_t_array) * BAR_PER_PASCAL
        final_volume_ml = v_t_array[-1] * ML_PER_M3
        max_volume_ml = np.max(v_t_array) * ML_PER_M3

        results = f"""SIMULATION RESULTS
{'='*40}
Time: {self.params['end_time'] * MS_PER_S:.3f} ms
Points: {len(sol.t)}
Success: {sol.success}

DART RESULTS
{'-'*20}
Final Position: {final_dart_pos_mm:.3f} mm
Final Velocity: {final_dart_vel_fps:.3f} fps
Max Velocity: {max_dart_vel_fps:.3f} fps

PLUNGER RESULTS  
{'-'*20}
Final Position: {final_plunger_pos_mm:.3f} mm
Final Velocity: {final_plunger_vel_fps:.3f} fps
Max Velocity: {max_plunger_vel_fps:.3f} fps

SYSTEM RESULTS
{'-'*20}
Final Pressure: {final_pressure_bar:.3f} bar
Min Pressure: {min_pressure_bar:.3f} bar
Final Volume: {final_volume_ml:.3f} mL
Max Volume: {max_volume_ml:.3f} mL
"""
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, results)
    
    def run_simulation_threaded(self):
        """Run simulation in thread to prevent GUI freezing"""
        self.status_label.config(text="Running simulation...", foreground="orange")
        thread = threading.Thread(target=self.run_simulation)
        thread.daemon = True
        thread.start()
    
    def save_parameters(self):
        """Save current parameters to a pickle file"""
        try:
            self._update_params_from_vars()
        except tk.TclError as e:
            messagebox.showerror("Error", f"Invalid parameter value: {e}")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Parameter Set",
            defaultextension=".pkl",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'wb') as outfile:
                pickle.dump(self.params, outfile)
            self._update_file_label(file_path)
            self.status_label.config(text="Parameters saved successfully", foreground="green")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save parameters: {exc}")
            self.status_label.config(text="Parameter save failed", foreground="red")
    
    def load_parameters(self):
        """Load parameters from a pickle file and rerun the simulation"""
        file_path = filedialog.askopenfilename(
            title="Load Parameter Set",
            filetypes=[("Pickle files", "*.pkl *.pickle"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'rb') as infile:
                loaded_params = pickle.load(infile)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load parameters: {exc}")
            self.status_label.config(text="Parameter load failed", foreground="red")
            return
        
        if not isinstance(loaded_params, dict):
            messagebox.showerror("Error", "Loaded file does not contain a valid parameter set.")
            self.status_label.config(text="Parameter load failed", foreground="red")
            return
        
        missing_keys = [key for key in self.params if key not in loaded_params]
        if missing_keys:
            messagebox.showerror("Error", f"Loaded parameter set is missing keys: {', '.join(missing_keys)}")
            self.status_label.config(text="Parameter load failed", foreground="red")
            return
        
        self.params.update(loaded_params)
        
        for key, value in self.params.items():
            try:
                display_value = self._param_to_display(key, value)
                self.param_vars[key].set(display_value)
            except tk.TclError:
                messagebox.showerror("Error", f"Invalid value for parameter '{key}': {value}")
                self.status_label.config(text="Parameter load failed", foreground="red")
                return
        
        self._update_file_label(file_path)
        self.status_label.config(text="Parameters loaded successfully", foreground="green")
        self.run_simulation_threaded()
    
    def _update_params_from_vars(self):
        """Sync internal param dict from GUI variables"""
        for key, var in self.param_vars.items():
            display_value = var.get()
            self.params[key] = self._param_from_display(key, display_value)

    def _param_to_display(self, key, value):
        """Convert internal SI value to display units"""
        converter = self.display_converters.get(key)
        if converter:
            to_display, _ = converter
            return to_display(value)
        return value

    def _param_from_display(self, key, value):
        """Convert display units to internal SI value"""
        converter = self.display_converters.get(key)
        if converter:
            _, to_internal = converter
            return to_internal(value)
        return value
    
    def _update_file_label(self, file_path):
        """Update the label showing the current parameter file name"""
        self.current_param_file = file_path
        if file_path:
            filename = Path(file_path).stem
            self.file_label.config(text=f"Parameter file: {filename}")
        else:
            self.file_label.config(text="No parameter file selected")

def main():
    root = tk.Tk()
    root.lift()
    root.focus_force()
    try:
        root.attributes("-topmost", True)
        root.after(100, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass
    app = DartPlungerSimulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
