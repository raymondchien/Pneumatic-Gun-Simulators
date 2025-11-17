import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.integrate import solve_ivp
import tkinter as tk
from tkinter import ttk, messagebox
import threading

class SpringerSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Nomad Simulation Calculator")
        self.root.geometry("1400x900")  # Larger window
        
        # Default parameters
        self.params = {
            'p_0': 583633,      # Initial pressure in Pascals
            'p_2': 101325,           # Ambient pressure in Pascals
            'D': 0.013,         # Diameter in meters
            'gamma': 1.4,       # Adiabatic index
            'v_0': 1.74e-5,     # Initial volume in cubic meters
            'v_expand': .5e-5, # Expansion Chamber volume
            'mass': 0.0012,     # Mass in kg
            'fric1': 4,         # Static friction force in Newtons
            'fric2': 0.2,       # Dynamic friction term
            'end_time': 0.02,   # Simulation end time
            'n_points': 1500    # Number of evaluation points
        }
        
        self.setup_gui()
        self.run_simulation()  # Initial simulation
        
    def setup_gui(self):
        # Create main frames with specific widths
        control_frame = ttk.Frame(self.root, width=300)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        control_frame.pack_propagate(False)  # Maintain fixed width
        
        plot_frame = ttk.Frame(self.root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(control_frame, text="Nomad Simulation Parameters", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Parameter controls
        self.create_parameter_controls(control_frame)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=20, fill=tk.X)
        
        run_button = ttk.Button(button_frame, text="Run Simulation", 
                               command=self.run_simulation_threaded)
        run_button.pack(fill=tk.X, pady=5)
        
        reset_button = ttk.Button(button_frame, text="Reset to Defaults", 
                                 command=self.reset_parameters)
        reset_button.pack(fill=tk.X, pady=5)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Ready", 
                                     foreground="green")
        self.status_label.pack(pady=10)
        
        # Create matplotlib figure
        self.create_plots(plot_frame)
        
    def create_parameter_controls(self, parent):
        # Create scrollable frame for parameters - make it more compact
        canvas = tk.Canvas(parent, height=500, width=280)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Parameter definitions with descriptions
        param_info = {
            'p_0': ('Initial Pressure (Pa)', 100000, 1000000),
            'p_2': ('Ambient Pressure (Pa)', 0, 200000),
            'D': ('Diameter (m)', 0.001, 0.1),
            'gamma': ('Adiabatic Index', 1.0, 2.0),
            'v_0': ('Initial Volume (m³)', 1e-6, 1e-3),
            'v_expand': ('Expansion Volume (m³)', 1e-6, 1e-3),
            'mass': ('Mass (kg)', 0.0001, 0.01),
            'fric1': ('Static Friction (N)', 0, 50),
            'fric2': ('Dynamic Friction (N)', 0, 10),
            'end_time': ('End Time (s)', 0.001, 1.0),
            'n_points': ('Number of Points', 100, 5000)
        }
        
        self.param_vars = {}
        self.param_entries = {}
        
        for i, (key, (label, min_val, max_val)) in enumerate(param_info.items()):
            # Create frame for each parameter
            param_frame = ttk.Frame(scrollable_frame)
            param_frame.pack(fill=tk.X, pady=5)
            
            # Label
            ttk.Label(param_frame, text=label, width=20).pack(side=tk.LEFT)
            
            # Entry
            var = tk.DoubleVar(value=self.params[key])
            self.param_vars[key] = var
            
            entry = ttk.Entry(param_frame, textvariable=var, width=12)
            entry.pack(side=tk.LEFT, padx=5)
            self.param_entries[key] = entry
            
            # Bind enter key to run simulation
            entry.bind('<Return>', lambda e: self.run_simulation_threaded())
            
    def create_plots(self, parent):
        # Create matplotlib figure with subplots - larger figure size
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(
            2, 2, figsize=(12, 10))
        self.fig.suptitle('Nomad Simulation Results', fontsize=18)
        
        # Adjust spacing between subplots
        self.fig.subplots_adjust(left=0.08, bottom=0.08, right=0.95, top=0.92, 
                                wspace=0.25, hspace=0.35)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def system(self, t, x1x2):
        """Define the system of first-order ODEs"""
        x1, x2 = x1x2  # unpack position and velocity
        
        # Calculate area
        area = np.pi * (self.params['D']**2) / 4
        
        # Calculate volume and pressure at current position
        v_t = self.params['v_expand']+self.params['v_0'] + area * x1 
        p_t = (self.params['p_0'] / ((v_t / self.params['v_0']) ** self.params['gamma']))
        
        # Set the equations
        dx1dt = x2  # velocity
        
        # Choose friction based on position
        friction = self.params['fric1'] if x1 <= 0.03 else self.params['fric2']
        
        # Calculate acceleration
        pressure_force = (p_t - self.params['p_2']) * area
        dx2dt = (pressure_force - friction) / self.params['mass']
        
        return [dx1dt, dx2dt]
        
    def run_simulation(self):
        try:
            # Update parameters from GUI
            for key, var in self.param_vars.items():
                self.params[key] = var.get()
            
            # Initial conditions
            x0 = [0, 0]  # Initial state [x(0), x'(0)]
            t_span = (0, self.params['end_time'])
            t_eval = np.linspace(0, self.params['end_time'], int(self.params['n_points']))
            
            # Solve ODE
            sol = solve_ivp(self.system, t_span, x0, t_eval=t_eval)
            
            if not sol.success:
                raise Exception("ODE solver failed")
            
            # Calculate derived quantities
            area = np.pi * (self.params['D']**2) / 4
            v_t = self.params['v_expand']+self.params['v_0'] + area * sol.y[0]
            p_t = self.params['p_0'] / ((v_t / self.params['v_0']) ** self.params['gamma'])
            
            # Clear previous plots
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()
            
            # Plot 1: Position vs Time
            self.ax1.plot(sol.t, sol.y[0], 'b-', linewidth=2)
            self.ax1.set_xlabel('Time (s)')
            self.ax1.set_ylabel('Position (m)')
            self.ax1.set_title('Position vs Time')
            self.ax1.grid(True)
            
            # Plot 2: Velocity vs Time
            self.ax2.plot(sol.t, sol.y[1], 'r-', linewidth=2)
            self.ax2.set_xlabel('Time (s)')
            self.ax2.set_ylabel('Velocity (m/s)')
            self.ax2.set_title('Velocity vs Time')
            self.ax2.grid(True)
            
            # Plot 3: Volume vs Time
            self.ax3.plot(sol.t, v_t, 'm-', linewidth=2)
            self.ax3.set_xlabel('Time (s)')
            self.ax3.set_ylabel('Volume (m³)')
            self.ax3.set_title('Volume vs Time')
            self.ax3.grid(True)
            
            # Plot 4: Pressure vs Time
            self.ax4.plot(sol.t, p_t, 'c-', linewidth=2)
            self.ax4.set_xlabel('Time (s)')
            self.ax4.set_ylabel('Pressure (Pa)')
            self.ax4.set_title('Pressure vs Time')
            self.ax4.grid(True)
            
            # Update layout and canvas
            self.fig.tight_layout()
            self.canvas.draw()
            
            # Update status
            self.status_label.config(text=f"Simulation completed successfully", 
                                   foreground="green")
            
            # Display some key results
            max_pos = np.max(sol.y[0])
            max_vel = np.max(sol.y[1])
            min_pressure = np.min(p_t)
            
            result_text = f"Max Position: {max_pos:.6f} m | Max Velocity: {max_vel:.3f} m/s | Min Pressure: {min_pressure:.0f} Pa"
            self.status_label.config(text=result_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed: {str(e)}")
            self.status_label.config(text="Simulation failed", foreground="red")
    
    def run_simulation_threaded(self):
        """Run simulation in a separate thread to prevent GUI freezing"""
        self.status_label.config(text="Running simulation...", foreground="orange")
        thread = threading.Thread(target=self.run_simulation)
        thread.daemon = True
        thread.start()
    
    def reset_parameters(self):
        """Reset all parameters to default values"""
        defaults = {
            'p_0': 482633,
            'p_2': 0,
            'D': 0.013,
            'gamma': 1.4,
            'v_0': 1.74e-5,
            'mass': 0.0012,
            'fric1': 4,
            'fric2': 0.2,
            'end_time': 0.02,
            'n_points': 1500
        }
        
        for key, value in defaults.items():
            self.param_vars[key].set(value)
        
        self.run_simulation_threaded()

def main():
    root = tk.Tk()
    app = SpringerSimulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()