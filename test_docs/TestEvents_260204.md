Testing the DiskFreshMon program.

Used HDD: STHB12

Test_260204_01_01
2026.02.04 20:25
Application tested. Result False

reason: Does not step period state.

1. run without disk: Ok
2. run with disk, without app: Ok
3. run with disk, with app
    1. wait... Ok, Not Running appeared
    2. started DiskFresh process Ok monitoring started with all time.. or not? Log does not appeared... maybe failed!
    3. after a short time, does not step period to longer wait. Failed!

Test Failed!!

Test_260204_01_02
Javítás: 698-as sorban rosszul volt a képlet beírva, így nem kezelte a nulladik sort.

2026.02.04 21:24
Application tested. Result False

reason: Does not log on periods.

1. run without disk: Ok
2. run with disk, without app: Ok
3. run with disk, with app
    1. wait... Ok, "Not Running" appeared
    2. started DiskFresh process Ok monitoring started with all time.. Log does not appeared... Failed!
    3. after a short time, step period to longer wait. Ok! Correction successful!

Test Failed!

Javítás: 746-os sorban a kezdeti időből lett kivonva az aktuális idő, és ez kivonva a periódus időből, mely így hozzáadódott kivonás helyett.
    Cseréltem az iTime-datetime.now()-t datetime.now()-iTime-re

Test_260204_01_03
2026.02.04 21:30
Application tested. Result True

1. run without disk: Ok
2. run with disk, without app: Ok
3. run with disk, with app
    1. wait... Ok, "Not Running" appeared
    2. started DiskFresh process Ok monitoring started with all time.. Log appeared... Ok! Correction successful!
    3. after a short time, step period to longer wait. Ok!

Tesztelni kellene azt is, hogy a végén kiírja-e a 100%-ot, illetve az aktuális, és teljes méret azonos lessz-e.

Illetve a leállítást is.

Test_260205_01_04
2026.02.05 15:50
Application test...

1. run with disk & app: Ok
2. Start process: Ok
3. Monitoring percent has no % sign after number, and not enough deep... need 2 digit after point. 
    In this case 0.01%: 0.7s if 2 hours the whole process. But we have 20 hours process too (7s: 0.01%).
Test Failed!!
The process stopped when I pressed button on other application
Must to use an inside keyboard listener.

Test_260208_1009_01_05
1. run without disk: Ok
2. run with disk, without app: Ok
3. run with disk, with app: Ok
4. Percent 2 digit accurate, not enough, need 3.

Test_260208_1012_01_06
1. run with disk, with app: Ok
2. Percent 2 digit accurate, not enough, need 3.

Test_260208_1029_01_06
Changed te period watch time to 96%
1. run with disk, with app: Ok
2. Percent 2 digit accurate, not enough, need 3.

Test_260208_1035_01_06
Changed te period watch time to 96%
Percent 3 digit accurate
Full run (over 2 hours)
1. run with disk, with app: Ok
2. Percent 3 digit: Ok
3. The parcent time check too late!
    Need to change back watch time!
4. Last data on 260208_1303(34.8)
    The end maybe on 260208_1303(35.1)
No end checking. Try to catch the value after last data!

For faster proccess we try HDD045 to monitoring.

Test_260208_1339_01_06
1. run with disk, with app: Ok


Full time expected 1:20:00... not the best.

Speed is 0.00... something is wrong!
But an all test! The calculation is very worst.

HDD0057
Test_260208_1348_01_06
1. run with disk, with app: Ok

Expected length is 3:10... too long.

back to HDD045
Inserted to code debug print for end string

Test_260208_1351_01_06
HDD045
1. run with disk, with app: Ok
2. Period values Ok!
3. Checked end string: #32 20h

Vég 260208_150657.75

Kis partíció létrehozása, hogy legyen rövid teszt üzem is!
Test_260208_1740
1. run with disk, with app: Failed: no > operator for str and int.
Developer left int(var) where stored drive data to object(cDisk)

HDD045-ön
Kilépő karakter: Space!

Test_260208_174343.9_01_06
HDD045(TesztDrive)
1. run with disk, with app: Ok (Correction succesful)
2. Period values Ok!
3. Checked end string: #32 20h: Ok!

Remove Debug prints!

Last test for the day:
Test_260208_1754_01_06
HDD045(TesztDrive)
1. run with disk, with app: Ok (Correction succesful)
2. Period values Ok!
3. Checked end string: #32 20h: Ok!
The first log missing, where aktual value is 0.

Test_260208_1805_01_06
HDD045(TesztDrive)
1. run with disk, with app: Ok (Correction succesful)
2. monitoring failed, date parameter too small.
    We used bad variable, the prevoius value. It's "zero"
And it needed to print de exact timestemp of the process in the beginning.

Test_260208_1810_01_06
The begin time printed after init. It must to bring back.

Test_260208_1817_01_06
1. run with disk, with app: Ok
2. Begin text printed on his place. Ok

Test_260208_181917.5_01_06
1. run with disk, with app: Ok
2. Begin text printed on his place. Ok
3. Monitoring started time printed. Ok (But with false text: Last! change to First!)
4. Periods:Ok
5. Last value printed: Ok.
6. Stopped the script: Ok.
7. Win32 Error: Failed, appeared.

Last defect is the Win32 Error.




