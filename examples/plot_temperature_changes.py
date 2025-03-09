import matplotlib.pyplot as plt
import pandas as pd

# Load the data from CSV file
weather_data = pd.read_csv('simulated_weather_data.csv')

# Convert 'Date' column to datetime format
weather_data['Date'] = pd.to_datetime(weather_data['Date'])

# Plotting the temperature changes over time
plt.figure(figsize=(10, 5))
plt.plot(weather_data['Date'], weather_data['Max Temperature'], label='Max Temperature', color='tab:red')
plt.plot(weather_data['Date'], weather_data['Min Temperature'], label='Min Temperature', color='tab:blue')
plt.title('Temperature Changes Over Time in Beijing (Simulated Data)')
plt.xlabel('Date')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save the plot to an image file
output_image = 'temperature_changes.png'
plt.savefig(output_image)

print(f'Temperature changes curve has been saved to {output_image}')