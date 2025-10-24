import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp, cumulative_trapezoid

# Parameters - defined once at the top
p_0 = 501325  # Initial pressure in Pascals
p_2 = 101325       # Ambient pressure in Pascals 
D = 0.013        # Diameter in meters
gamma = 1.4      # Adiabatic index cp/cv for air
v_0 = 1.74e-5    # Initial volume in cubic meters
mass = 0.0012    # Mass in kg
fric1 = 0.4      # Static friction force in Newtons
fric2 = 0.2      # Dynamic friction term
leakage_constant = 30000  # Leakage constant in Pa/s **unused**
area = np.pi * (D**2) / 4  # Cross-sectional area (calculated once)

def system(t, x1x2):
    """Define the system of first-order ODEs"""
    x1, x2 = x1x2  # unpack position and velocity
    
    # Calculate volume and pressure at current position
    v_t = v_0 + area * x1
    p_t = (p_0 / ((v_t / v_0) ** gamma))
    
    # Set the equations
    dx1dt = x2  # velocity
    
    # Choose friction based on position
    friction = fric1 if x1 <= 0.005 else fric2 #play with this
    
    # Calculate acceleration (factoring out common terms)
    pressure_force = (p_t - p_2) * area
    dx2dt = (pressure_force-fric1) / mass
    
    return [dx1dt, dx2dt]

# Initial conditions
x0 = [0, 0]  # Initial state [x(0), x'(0)]
end_time = .05
# Time span for the solution (start, end)
t_span = (0, end_time)

# Time points where solution is computed
t_eval = np.linspace(0, end_time, 1500)

# Solve the system of ODEs
sol = solve_ivp(system, t_span, x0, t_eval=t_eval)

# Calculate derived quantities using the same parameters
v_t = v_0 + area * sol.y[0] # Volume at time t
p_t = p_0 / ((v_t / v_0) ** gamma)      # Pressure over time equation

# Create three separate plots
fig, ( ax2, ax3, bx1,bx2) = plt.subplots(4, 1, figsize=(10, 12))


# Plot 2: Velocity vs Time
ax2.plot(sol.t, sol.y[0], 'b-', linewidth=2, label="Position x(t)")
ax2.set_xlabel('Time (sec)')
ax2.set_ylabel('Position (m)')
ax2.set_title('Position vs Time')
ax2.legend()
ax2.grid(True)

# Plot 3: Acceleration vs Time
ax3.plot(sol.t, sol.y[1], 'r-', linewidth=2, label="Velocity x'(t)")
ax3.set_xlabel('Time (sec)')
ax3.set_ylabel('Velocity (m/s)')
ax3.set_title('Velocity vs Time')
ax3.legend()
ax3.grid(True)


# Plot 1: Volume vs Time
bx1.plot(sol.t, v_t, 'm-', linewidth=2, label="Volume v_t")
bx1.set_xlabel('Time (sec)')
bx1.set_ylabel('Volume (m³)')
bx1.set_title('System Volume vs Time')
bx1.legend()
bx1.grid(True)

# Plot 2: Pressure vs Time
bx2.plot(sol.t, p_t, 'c-', linewidth=2, label="Pressure p_t")
bx2.set_xlabel('Time (sec)')
bx2.set_ylabel('Pressure (Pa)')
bx2.set_title('Pressure vs Time')
bx2.legend()
bx2.grid(True)

plt.tight_layout()
plt.show()
