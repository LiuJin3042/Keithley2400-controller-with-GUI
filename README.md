# Keithley2400-controller-with-GUI
Simple python program to allow you set and read from 2400 source meter.
<img width="1000" height="828" alt="image" src="https://github.com/user-attachments/assets/600c13a5-828f-42b5-b0fd-3665219f3223" />
1. connect the source meter to the computer through gpib.
2. select the correct address, choose the measure mode.
3. manually input the voltage/current list you want to test.
4. you may generate a test sequence automatically in here.
<img width="566" height="93" alt="image" src="https://github.com/user-attachments/assets/12fdff3e-e4fe-4fb0-834c-ec05eeba648d" />

5. set the duration per point and measurement interval. tips, if you want to do constant voltage measurement, you can set the duration to a very large number, so the voltage will stay at the first voltage in your test sequence.
6. select path to save the file. this programme will not overwrite previous files.
7. start measurement! 
