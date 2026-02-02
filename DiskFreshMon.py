# ==============================================================================
#  DiskFreshMon DiskFresh applikáció figyelő program
# ==============================================================================

# ==============================================================================
# 📥️ Modulok behívása
# ==============================================================================

# 📥💿 Modul a winchester kiolvasáshoz
import wmi

#import pythoncom # Kelleni fog a WMI miatt a COM inicializáláshoz

# 📥🗔 Modul a célprogram lekérdezéshez
from pywinauto.application import Application,WindowSpecification
from pywinauto.findbestmatch import MatchError
from pywinauto.findwindows import ElementNotFoundError

# 📥📂 Modul a log mentéséhez
import os

# 📥🕰 Modul az idő olvasáshoz
import time

# 📥⏱ Modul az időzítéshez
from pywinauto.timings import TimeoutError, wait_until
from dataclasses import dataclass,replace

# 📥⌨
from pynput.keyboard import Key,KeyCode, Listener

# 📥📝 Modul a logoláshoz
from datetime import datetime,timedelta

# 📥🔱 Modul a szálkezeléshez az időzítésen belül (billentyűfigyelés)
import threading

from typing import Union

# ==============================================================================
# 🛠️ PARAMÉTEREK BEÁLLÍTÁSA
# ==============================================================================

# 🛠💿
#  Rutinon belül vannak a paraméterek

# 🛠🗔
wTitle="DiskFresh"
wLabelID=1004
owDiskFresh: WindowSpecification
oLabel : WindowSpecification # Állapotsor


# 🛠⏱
sLabelInit="Not Running" # Kezdeti értéke az állapotsornak
sStrtTO=30 # Indulásra várakozás limitje (secundumban)
# indulásra várakozás időnként megszakad. Ilyenkor ellenőrzi, hogy pl.
#  Esc-el ki akarunk-e lépni.

# 🧬 Intervalum osztály
@dataclass
class oFigyel:
    period: int = 30
    length: float = 300.0

lFigyelő=[oFigyel(1,7) # 1s Kezdettől/Végétől vissza 7 másodperctől
            ,oFigyel(5,15) # 5s Kezdettől/Végétől vissza 15 másodperctől
            ,oFigyel(10,60) # 10s Kezdettől/Végétől vissza 1 percig
            ,oFigyel(30,300) # fél percenként Kezdettől/Végétől vissza 5 percig
            ,oFigyel(300,1200) # Kezdettől 5 percenként 20 percig
            ,oFigyel(900,5400) # Kezdettől 15 percenként 1,5 óráig
            ,oFigyel(3600,864000) # óránként 10 napig..
            ]
vFigyel=0 # 0 az első érték
# Nagyon fontos! a pause, az
#  vagy 0,1-s onként fut de végig
#   (ez óránkénti naplózásnál igen felesleges 36000 UI lekérés és számolás)
#  vagy a periódus tizede. esteleg 20-a, ezáltal elég pontos a logolás.
#   És nincs felesleges számolgatás.
# Trigger: Kezdettől előző osztály length leteltekor indul.
#          Végétől saját length érték elérésekor indul.
# Figyelő megnézi kezdettől, végétől, és a kissebb értéket figyelembe véve
#  választja ki a legnagyobb hosszt.
#  Ha az így kiválasztott nem az aktuális, akkor vált.
# Persze úgy is nézhetjük, hogy nem foglalkozunk, aktuális-e vagy sem,
#  mivel úgyis az elejétől nézzük a periódust.
#  Mindig az adott helyzethez viszonyítunk
#
# Amire még figyelnünk kell, a lassítás, illetve gyorsítás.
#  Ha lassítunk, akkor lassabb ütembe lépve tartsuk meg az immár gyorsabb
#   erőltetést?
#  Ha lassítunk, akkor eredetinél gyorsabb (közeledünk a célhoz) ütembe lépve
#   tartsuk meg az erőltetést, maradjunk lassabbak,
#   és csak az utolsó bejegyzést, azt is pontatlanabbul rögzítsük?
#  Persze ugyanez a kérdés gyorsításnál is.
#  Vagy csak az arányt tartsuk meg, és úgy "közelítsünk"?

# keresés normál módon
## Ez a sor NEM másolja le a listát, csak egy "szabályt" hoz létre
#kisebbek_indexei = (i for i, obj in enumerate(sFigyelő) if obj.length <= 1226)
## Kikeressük a maximum indexet a feltétel alapján
#best_index = max(kisebbek_indexei, key=lambda i: sFigyelő[i].length, default=None)

# import bisect
# kereső: bisect.bisect_right(sFigyelő, keresett_ertek, key=lambda x: x.length)

# 🧬 Log osztály
@dataclass
class cLog:
    TimeStamp: datetime #= field(default_factory=datetime.now)
    Akt: int = 0
    length: int = -1 # Sectorok száma
# sLogs=[oLog]

listener: Listener

# ==============================================================================
# 💿️ Lemez kezelő eljárások
# ==============================================================================
# ==============================================================================
# 💿💬 Lemez cimke, S# olvasás
# ==============================================================================

def gDiskProps():
    # lekérjük a lemez adatait: Gyáriszám, sectorokszáma, köteg cimkéje.
    # USB-re csatolt merevlemez adatait igyekszünk lekérni.
    #  Ha több van csatolva, akkor bajban vagyunk...
    #  Lehet paraméterezni is kellene? Ha van paraméter,
    #  akkor azt a drive-t olvassuk be.
    # Tehát nem a PenDrive-t
    
    # 🛠️ PARAMÉTEREK BEÁLLÍTÁSA
    # Ezek a paraméterek csak ehhez a funkcióhoz kellenek,
    #  ezért nem a fő paraméterek között vannak
    cBUS_USB = 7
    nsStorage = 'root/Microsoft/Windows/Storage'

    #pythoncom.CoInitialize()

    # ▶️
    try:
        WMIstr = wmi.WMI(namespace=nsStorage)
        WMIcm2 = wmi.WMI()

        MSFT_PDs=WMIstr.MSFT_PhysicalDisk(BusType=cBUS_USB)
        if not MSFT_PDs:
            return "No USB Drives"
        prt=None
        #iMaxPSz=0
        iMaxLSz=0
        for PDisk in MSFT_PDs:
            # print('Fnd:', PDisk)
            v_PD_Name=PDisk.FriendlyName

            sDrvID=getattr(PDisk,'DeviceID', None)
            if sDrvID is None: continue

            DDs=WMIcm2.Win32_DiskDrive(Index=sDrvID)
            if not DDs: continue
            DD=DDs[0] # Feltételezhetően csak egy van
            
            for DP in DD.associators(wmi_result_class="Win32_DiskPartition"):
                #if iMaxSz<DP.Size:
                #    iMaxSz=DP.Size
                for DL in DP.associators(wmi_result_class="Win32_LogicalDisk"):
                    if iMaxLSz<int(DL.Size):
                        iMaxLSz=DL.Size
                        iFree=DL.FreeSpace
                        iLabel=DL.VolumeName
                        iDrLt=DL.Caption
                        ilSctS=DD.BytesPerSector                        
                        ilSctN=DD.TotalSectors
                        iPDSN=DD.SerialNumber
                        iMdTp=DD.MediaType
        if iMaxLSz==0:return "No drive"    
        prt={"S#":iPDSN, "ID":iLabel, "Drv":iDrLt, "Media":iMdTp, "Sct":ilSctN # pyright: ignore[reportPossiblyUnboundVariable]
             , "BPSct":ilSctS,"Size":iMaxLSz,"Free":iFree} # pyright: ignore[reportPossiblyUnboundVariable]
        return prt
    except Exception as e:
        return f"Kritikus hiba a WMI lekérdezés során: {e}"
    #finally:
    #    # Kifejezetten elengedjük a COM-ot
    #    pythoncom.CoUninitialize()
            

# ==============================================================================
# 🗔💬 DiskFresh olvasás
# ==============================================================================

# ==============================================================================
# 🗔 Ablak keresés
# ==============================================================================

def getwDiskFresh():
    """
    Kapcsolódik a 'DiskFresh' ablakhoz, és inicializálja a főablak, 
    valamint az 1004-es ID-jű Static vezérlő objektumait.
    """
    #global owDiskFresh, oLabel
    global owDiskFresh, oLabel
    print(f"[{'INIT'.center(6)}] Keresés: '{wTitle}' ablak...")

    try:
        # Kapcsolódás a 'DiskFresh' ablakhoz címrészlet alapján

        #Debug
        print('App_Tmp:',wTitle)
        app = Application(backend="win32").connect(
            title_re=f".*{wTitle}.*"
            ,class_name="#32770"
            #,path=r"C:\Program Files\DiskFresh\DiskFresh.exe"
        )
        #Debug
        #print('AppTxt:',app.window_text())        
        
        # ==============================================================================
        # 🗔
        # ==============================================================================
        # Lekérjük a főablak objektumát
        owDiskFresh = app.top_window()
        # Debug
        print('Window:',owDiskFresh.window_text())
        print('WinClass:', owDiskFresh.class_name())
        
        # ==============================================================================
        # ▭
        # ==============================================================================
        # Lekérjük a Static vezérlőt ID alapján
        oLabel = owDiskFresh.child_window(control_id=wLabelID, class_name="Static")
        
        print(f"[{'INIT'.center(6)}] ✅ Sikeresen inicializálva a vezérlő (ID: {wLabelID}).")
        return True
    
    except ElementNotFoundError as e:
        print(f"[{'INIT'.center(6)}] ❌ Hiba (ElementNotFoundError): Az ablak '{wTitle}' nem található.")
        return False
    except MatchError as e:
        print(f"[{'INIT'.center(6)}] ❌ Hiba: Nem található ablak vagy vezérlő.")
        print(f"[{'INIT'.center(6)}] Részletes hiba: {e}")
        # Visszaadunk False-t, jelezve, hogy az inicializálás sikertelen volt
        return False
    except Exception as e:
        print(f"[{'INIT'.center(6)}] ❌ Hiba (Általános): {e}")
        return False


# ==============================================================================
# 👀 Kilesni a program állapotsorából az aktuális értéket
# ==============================================================================

def getLabelValue():
    """
    Ellenőrzi, hogy a DiskFresh ablak létezik-e még, és ha igen, 
    kiolvassa és visszaadja az 1004-es Static vezérlő aktuális szövegét.
    """
    global oLabel
    vRes=""
    
    # 1. Ellenőrizzük, hogy inicializálva van-e a Static vezérlő
    if oLabel is None:
        print(f"[{'CHECK'.center(6)}] ⚠️ Figyelem: A vezérlő nincs inicializálva. Próbálja újra az inicializálást.")
        return "None"
    
    # 2. Ellenőrizzük, hogy a vezérlő (és így a szülő ablak is) még létezik-e
    if oLabel.exists():
        vText=""
        vRes=""        
        try:
            # 3. Lekérjük az aktuális szöveget
            vText = oLabel.window_text()
            # Várakozás vátozásig
            wait_until(
                timeout=10 # a timeout változik a folyamattól függően.
                , retry_interval=0.1
                , func=lambda: (((vRes:=oLabel.window_text()) and 0) or vRes!= vText)
                #, func=lambda: vRes:=sStop or (oLabel.window_text() != vText)
            )            
            
            print(f"[{'CHECK'.center(6)}] ✅ Ablak aktív. Aktuális szöveg: **{vRes}**")
            return vRes
        
        except TimeoutError:
            return vText+" TimeOut" 
        except Exception as e:
            # Bár az exists() lefutott, még történhet hiba a szöveg lekérésénél (ritka)
            print(f"[{'CHECK'.center(6)}] ❌ Hiba a szöveg lekérésekor: {e}")
            return "Error"
    else:
        print(f"[{'CHECK'.center(6)}] 🛑 A vezérlő vagy a 'DiskFresh' ablak bezáródott/megszűnt.")
        return "Closed"

# ==============================================================================
# 🤔💬 Aktuális értéket értelmezni
# ==============================================================================

def AktValues(sv): # sv: státusz sor szövege
    vSV=sv.replace(',','')
    lSV=vSV.split()

    vDT=datetime.now()
    if sv[-7:]=="TimeOut": # right(sv,7)="TimeOut"
        vDT=vDT-timedelta(seconds=10) # 10 sec is the timeout        
    
    # Ha nem adat van, akkor a szöveget küldi vissza.
    if len(lSV>3):
        if lSV[0].isdigit() and lSV[3].isdigit():
            return cLog(vDT,lSV[0],lSV[3])
        else:
            return sv
    else:
        return sv

    # Minta a számok keresésére, elhagyva a vesszőket:
    # \d+ illeszkedik egy vagy több számjegyre (0-9)
    # [,\d]* illeszkedik nulla vagy több vesszőre VAGY számjegyre (így "befogja" a vesszővel elválasztott számokat)
    # A csoportosító zárójelek () jelölik azokat a részeket, amiket ki akarunk nyerni.
    
    # pattern = r"([\d,]+) sectors of ([\d,]+) sectors refreshed"

    # match = re.search(pattern, sv)

def getAktVal():
    return AktValues(getLabelValue())


# ==============================================================================
# 💿🖋 Lemez frissítés Monitorozása
# ==============================================================================

# Három lépés
# Első, megvárni hogy el legyen indítva a frissítés.
#  Itt lényeges az utolsó "üres" érték időpontja, ha a kezdeti érték nem nulla.

# Lehetőségek:
#  Időn belül elindítják
#   Ez esetben megkapjuk az új értéket, de nem tudjuk, mikor volt a régi érték.
#   Illetve csak gyaníthatjuk, hogy tized másodperce.
#   Logolni kell a még 0 értéket, rögzíteni a kezdeti időpontot
#   És logolni kell az első mérést is.
#  Időn túl
#   Újra kell indítani az időt a stop szemafore ellenőrzésével
#  Már megy
#   Pár mérés után pl, 1 perc, meghatározni, hogy mikor indulhatott el,
#   és rögzíteni a 0 pontot, időpontot, stb.
#   Valahogy jelezni kellene, hogy a mérés kezdete kalkulált.
#    Esetleg a log mező bővíthető egy kalk jelzővel.

# Második, felfutó ág
#  Mi a gond a mérésnél?
#   az egységnyi idő, lehet akár majdnem 3 sec is, egy lassabb winyő esetében.
#   Tehát, minden mérésnél, így az első mérésnél is (Init)
#   Meg kell határozni az egységnyi időt.
#  a mérés várható ideje elött az egységnyi idő*5-el
#   meg kell kezdeni a lépegetést, és cache-be letárolni
#   addig, míg a mérés ideje a két érték között nem lesz.
#  Tehát, rögzítenem kell 16:00:00-kor van értékem
#   15:59:58.167 1220
#   15:59:59.725 1221
#   16:00:01:284 1222
# Akkor a mérés értéke 1221 lesz, az ideje meg 15:59:59.725,
#  illetve az egység: 1.559 sec
#
# És még arra kell figyelni, hogy ha a mérési táv
#  kissebb mint az egység hatszorosa, akkor már nem időt figyelünk,
#  hanem változást nézzük.

# Tehát... pl. óránként: pausa 3 perc (óra 20-a). ellenőrizni az időket, változik-e bármi,
#  volt-e gombnyomás, gyorsítás, lassítás, stb.
#  Míg az idő óránkénti osztás -  5xegységidő.
# Igen: Változás figyelés, míg átlépi az időt (órát)
#  Előző érték, előző idővel átad, egységidő az időkülönbség.
#
# Ha egységidő kissebb mint 0.1 sec, akkor figyelmen kívűl hagyhatjuk.

# Harmadik, lefutó ág
#  Megáll, mikor már nem logot ad az értékelő

# ==============================================================================
# 🧐⌨
# ==============================================================================

def on_press(key: Union[Key, KeyCode, None]) -> None:
    if key == Key.esc or (isinstance(key, KeyCode) and key.char!=None and key.char.lower() == 'q'):
        evPeriod.set() # Azonnal felébreszti a wait()-et
        sStop=True # Azonnal leállítja az wait_untilt.
        #return False

# Fő program inicializálása
def init():
    global evPeriod
    evPeriod = threading.Event()
    global listener
    listener = Listener(
        on_press=on_press
        )

    listener.start()
    pass

# Fő program blokk

def main_process():
    #vDP=gDiskProps()
    vDP="Test"
    print("Disk props:", vDP)

    if not isinstance(vDP, list):
        return False
    #return
    # Mely adatok vannak meg,
    #  Illetve mely adatok lesznek meg,
    #  Illetve mely adatokat logoljuk?
    #
    # Meg vannak:
    #  Drive (E:\)
    #  Cimke (STHC07)
    #  Serial numero:
    #  Méret GB: 1 TB
    #  Méret Sector: 1 953 525 168
    #  Szabad terület 23 GB
    #
    # Logolás indulásakor
    #  Össz Sectorméret (amit a program lát)
    #  Kezdeti időpont
    #
    # Mik lesznek meg?
    #  ReFresh idő: 29:54:59
    #  ReFresh idő/GB: 0:01:47,7
    #  ReFresh idő/MSector: 93,0 s/MSct
    #  ReFresh Sector/min: 921 329 Sct
    #  ReFresh Sector/Nap: 1,2 TSct/d
    #  ReFresh akt első 5 perc: 1,7 TSct/d
    #  ReFresh akt utolsó 5 perc: 0,83 TSct/d
    #
    # Logolható értékek
    #  Aktuális idő
    #  Aktuális Sectorszám
    #  Össz Sectorszám
    #
    # Kalkulált értékek
    #  Várható teljes idő
    #  Várható idő az Elkészűlésre
    #  Hátralevő idő


    # Státusz bárt megkeresni a DiskFresh alkalmazáson.
    # ? Pontosabban megvárni, hogy meglegyen az alkalmazás...

    # Egyenlőre nem várunk, ha nem fut a program, kilépünk...

    if not getwDiskFresh():
        return False

    # Program inicializálva
    #  A ciklus jön, mely ellenőrzi a státus sor értékét, és logolja
    #  A program futása közben, bármikor ki lehessen lépni a Q, Esc billentyűkkel.
    #    A ciklustól függetlenül lehessen lőni logot.
    #    ? A ciklust újraütemezve lehessen lőni logot.
    #       (pl. 05 kor indítottam a mérést, de egészkor akarom az órás logookat)
    # hm.. Lehessen átkapcsolni a logolást, hogy ne a kezdéshez,
    #  hanem az órához igazodjon a mérés ütemezése.

    sStop=False
    tBegin="Not Running"
    tEnd="Finished" # Nem biztos, hogy ez a szöveg!

    
    global vFigyel
    iTime=datetime.now()
    vHtr=0
    v_pSV=None
    
    while not sStop:
        # logolás
        jTime=datetime.now()
        vSV=getAktVal()
        if vSV==tBegin: # még nem indult el. Kell alapozni?
            # Olvasási Timeout átállítása nagyra, had várja míg elindul
            vFigyel=5 # 15p
        if vSV==tEnd: # elkészült, de teljesen
            break
        if isinstance(vSV, cLog): # adat!
            print(vSV)
            if vHtr<=0:
                # Elérte a határidőt, logolni kellene
                print(f"log: {vSV}")
                iTime=datetime.now()
                
            # ha elötte "indult", akkor a timeout visszaállítása gyorsra.
            #  Ne várjon akármeddig, mert kell a rész adat is
            
            # Figyelem! ez nem biztos, hogy logolandó...
            # Ellenőrizni kell a folyamat helyzetét, és ha szükséges váltani a
            #  Mélységet

            # a v_pSV tárolja az előző adatot.
            # Ebből kiszámolhatjuk az aktuális "sebességet", időt, stb.

            if not v_pSV is None: # van előző érték, tudjuk számolni a sebességet.
                # kell a kezdési idő
                # (vSV.TimeStamp-v_pSV.TimeStamp) st/r H/1-r H=st*(1-r)/r
                # (vSv.Akt-v_pSV.Akt)
                # H=(vSV.TimeStamp-v_pSV.TimeStamp)*(1/(vSv.Akt-v_pSV.Akt)-1)
                # vVég=vSV.TimeStamp+H
                # és kell a várható végső idő
                pass
            else: # Elvileg ez a kezdés... le kéne menteni...
                # a kezdés idejét
                # illetve logolni, hogy elkezdtük...
                iTime=datetime.now()
                vFigyel=0
            
            v_pSV=replace(vSV)
            
            pass
        
        # itt a folyamat mélységétől függ, meddig várjon.
        #  indulási állapotban várni 600-at (10p)
        #  Várni a periódus 20-adával,
        #  illetve ha a periódusig kevesebb az idő mint a huszada, akkor annyival.        
        if evPeriod.wait(timeout=min(
            lFigyelő[vFigyel].period # periódus idő
            ,vHtr:=lFigyelő[vFigyel].length # várakozási idő (nagy periódus)
            -(jTime-iTime).total_seconds() # eddig eltelt másodpercek az előző esemény óta
            )): # Vár periódus időt, de a hosszig.
            break # esemény kezelés gombnyomásra (most csak leáll)
        
                         
        pass



# ==============================================================================
# 🚀️ Program indítása.
# ==============================================================================

if __name__ == "__main__":
    try:
        init()
        main_process()
    finally:
        if "listener" in locals():
            listener.stop() # pyright: ignore[reportAttributeAccessIssue, reportUnboundVariable]
        time.sleep(1)
