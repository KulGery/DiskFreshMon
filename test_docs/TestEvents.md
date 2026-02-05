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
Applicatin test...

1. run with disk & app: Ok
2. Start process: Ok
3. Monitoring percent has no % sign after number, and not enough deep... need 2 digit after point. 
    In this case 0.01%: 0.7s if 2 hours the whole process. But we have 20 hours process too (7s: 0.01%).
Test Failed!!
The process stopped when I pressed button on other application
Must to use an inside keyboard listener.
