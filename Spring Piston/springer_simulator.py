import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp, cumulative_trapezoid

# Parameters - defined once at the top
p_0 = 101325  # Initial pressure inside plunger tube (assumed to be atmospheric)
p_2 = 101325       # Ambient pressure in Pascals 
D_b = 0.0127        # Diameter of barrel meters
D_p = 0.035052; #Diameter of plunger in meters 
gamma = 1.4      # Adiabatic index cp/cv for air
mass_d = 0.0012    # Mass of dart in kg
mass_p = 0.06    # Mass of plunger in kg
fric1 = 0.4      # Static friction force in Newtons
fric2 = 0.2      # Dynamic friction term
leakage_constant = 30000  # Leakage constant in Pa/s **unused**
area_b = np.pi * (D_b**2) / 4  # Cross-sectional area of the barrel (calculated once)
area_p = np.pi * (D_p**2) / 4  # Cross-sectional area of the plunger 

xso = 0.0254 #spring compression before priming (precompression) (m)
L_0 = 0.1016 #initial plunger length (m)
xsf = xso+L_0 #final total compression of spring 
k = 523*(11/5)  #spring constant n/m 
v_0 = L_0*area_p   # Initial volume in cubic meters

def system(t,x):
    d1,d2,p1,p2 = x # dart variables, plunger variables 
    
    #internal pressure term function, used in both equations
    p_t = p_0 / (((((L_0-p1)*area_p+(d1)*area_b)/v_0)) ** gamma)

    # Set the equations for the derivatives of the x vector 
    dd1dt = d2  
    dp1dt = p2 
    # Choose friction based on position
   # friction = fric1 if x1 <= 0.005 else fric2 #play with this
    
    # Calculate acceleration terms (factoring out common terms)
    dp2dt =  ((p_2-p_t)*area_p+(k*((xsf)-p1)))/mass_p
    dd2dt =  ((p_t-p_2)*area_b)/mass_d
    
    return [dd1dt,dd2dt,dp1dt,dp2dt]

#solver gives us position and velocities of the dart and plunger 


x0 = [0, 0,0,0]  # Initial state [d1(0), d2(0), p1(0), p2(0)]
end_time = .02
# Time span for the solution (start, end)
t_span = (0, end_time)

# Time points where solution is computed
t_eval = np.linspace(0, end_time, 1500)

# Solve the system of ODEs
sol = solve_ivp(system, t_span, x0, t_eval=t_eval)

# Calculate derived quantities for plotting
d1_pos = sol.y[0]  # Dart position
d1_vel = sol.y[1]  # Dart velocity
p1_pos = sol.y[2]  # Plunger position
p1_vel = sol.y[3]  # Plunger velocity

# Calculate pressure over time
p_t_array = p_0 / (((((L_0-p1_pos)*area_p+(d1_pos)*area_b)/v_0)) ** gamma)


# Calculate volume over time
v_t_array = ((L_0-p1_pos)*area_p) + (area_b*d1_pos)

# Calculate spring force over time
spring_force = k * (xsf - p1_pos)

# Create comprehensive plots
fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = plt.subplots(3, 2, figsize=(15, 12))

# Plot 1: Dart Position vs Time
ax1.plot(sol.t, d1_pos, 'b-', linewidth=2, label="Dart Position")
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Position (m)')
ax1.set_title('Dart Position vs Time')
ax1.legend()
ax1.grid(True)

# Plot 2: Dart Velocity vs Time
ax2.plot(sol.t, d1_vel, 'r-', linewidth=2, label="Dart Velocity")
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Velocity (m/s)')
ax2.set_title('Dart Velocity vs Time')
ax2.legend()
ax2.grid(True)

# Plot 3: Plunger Position vs Time
ax3.plot(sol.t, p1_pos, 'g-', linewidth=2, label="Plunger Position")
ax3.set_xlabel('Time (s)')
ax3.set_ylabel('Position (m)')
ax3.set_title('Plunger Position vs Time')
ax3.legend()
ax3.grid(True)

# Plot 4: Plunger Velocity vs Time
ax4.plot(sol.t, p1_vel, 'm-', linewidth=2, label="Plunger Velocity")
ax4.set_xlabel('Time (s)')
ax4.set_ylabel('Velocity (m/s)')
ax4.set_title('Plunger Velocity vs Time')
ax4.legend()
ax4.grid(True)

# Plot 5: Pressure vs Time
ax5.plot(sol.t, p_t_array, 'c-', linewidth=2, label="System Pressure")
ax5.set_xlabel('Time (s)')
ax5.set_ylabel('Pressure (Pa)')
ax5.set_title('System Pressure vs Time')
ax5.legend()
ax5.grid(True)

# Plot 6: Volume and Spring Force vs Time
ax6_twin = ax6.twinx()
line1 = ax6.plot(sol.t, v_t_array, 'orange', linewidth=2, label="System Volume")
line2 = ax6_twin.plot(sol.t, spring_force, 'purple', linewidth=2, label="Spring Force")
ax6.set_xlabel('Time (s)')
ax6.set_ylabel('Volume (m³)', color='orange')
ax6_twin.set_ylabel('Spring Force (N)', color='purple')
ax6.set_title('Volume and Spring Force vs Time')

# Combine legends
lines1, labels1 = ax6.get_legend_handles_labels()
lines2, labels2 = ax6_twin.get_legend_handles_labels()
ax6.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
ax6.grid(True)

plt.tight_layout()
plt.show()

# Print some key results
print("\n" + "="*60)
print("SIMULATION RESULTS SUMMARY")
print("="*60)
print(f"Simulation time: {end_time} seconds")
print(f"Number of data points: {len(sol.t)}")
print(f"Integration successful: {sol.success}")
print("-"*60)
print(f"Final dart position: {d1_pos[-1]:.6f} m")
print(f"Final dart velocity: {d1_vel[-1]:.3f} m/s")
print(f"Maximum dart velocity: {np.max(d1_vel):.3f} m/s")
print("-"*60)
print(f"Final plunger position: {p1_pos[-1]:.6f} m")
print(f"Final plunger velocity: {p1_vel[-1]:.3f} m/s")
print(f"Maximum plunger velocity: {np.max(p1_vel):.3f} m/s")
print("-"*60)
print(f"Final system pressure: {p_t_array[-1]:.0f} Pa")
print(f"Minimum system pressure: {np.min(p_t_array):.0f} Pa")
print(f"Final system volume: {v_t_array[-1]:.2e} m³")
print(f"Maximum system volume: {np.max(v_t_array):.2e} m³")
print("="*60)

