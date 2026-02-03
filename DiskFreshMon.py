# ==============================================================================
#  DiskFreshMon DiskFresh applikáció figyelő program
# ==============================================================================

# ==============================================================================
# 📥️ Modulok behívása
# ==============================================================================


#import pythoncom # Kelleni fog a WMI miatt a COM inicializáláshoz

# 📥🗔 Modul a célprogram lekérdezéshez
from pywinauto.application import Application,WindowSpecification
from pywinauto.findbestmatch import MatchError
from pywinauto.findwindows import ElementNotFoundError

# 📥💿 Modul a winchester kiolvasáshoz
import wmi

# 📥📂 Modul a log mentéséhez
#import os

# 📥🕰 Modul az idő olvasáshoz
import time

# 📥⏱ Modul az időzítéshez
from pywinauto.timings import TimeoutError, wait_until
from dataclasses import dataclass,replace,fields

# 📥⌨
from pynput.keyboard import Key,KeyCode, Listener

# 📥📝 Modul a logoláshoz
from datetime import datetime,timedelta

# 📥🔱 Modul a szálkezeléshez az időzítésen belül (billentyűfigyelés)
import threading

# 📥 Warnings kezelése ablak lekérdezéshez
import warnings

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
    check: float = 1.5
    period: int = 30
    length: int = 300

lFigyelő=[oFigyel(0,0,2) # legelején, legvégén mindent mérjünk!
            ,oFigyel(0.2,1,7) # 1s Kezdettől/Végétől vissza 7 másodperctől
            ,oFigyel(1,5,15) # 5s Kezdettől/Végétől vissza 15 másodperctől
            ,oFigyel(2,10,60) # 10s Kezdettől/Végétől vissza 1 percig
            ,oFigyel(6,30,300) # fél percenként Kezdettől/Végétől vissza 5 percig
            ,oFigyel(60,300,1200) # Kezdettől 5 percenként 20 percig
            ,oFigyel(180,900,5400) # Kezdettől 15 percenként 1,5 óráig
            ,oFigyel(720,3600,864000) # óránként 10 napig..
            ]
lFigyelőc=len(lFigyelő) #Figyelő lista darabszáma
vFigyel=0 # 0 az első érték
print(f"\nSzint: {vFigyel}\nCh: {lFigyelő[vFigyel].check} Pr: {lFigyelő[vFigyel].period} Ln: {lFigyelő[vFigyel].length}")
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
    TimeStamp: datetime=datetime.min #= field(default_factory=datetime.now)
    Akt: int = -1
    length: int = -1 # Sectorok száma
# sLogs=[oLog]

@dataclass
class cCalc:
    Percent: float =0
    TimeAktPrc: float=0
    SectorAktPrc: float=0
    TimeDPrc: float=0
    SectorDPrc: float=0
    ElapsedTimeu: timedelta=timedelta(0)
    ExpectedTimeu: timedelta=timedelta(0)
    Far: float=0
    DeltaTimeu: timedelta=timedelta(0)
    DeltaSectors: int=0
    TimePSectors: float=0
    SectorsPTime: float=0
    def _strip_ms(self, td: timedelta) -> timedelta:
        """Segédfüggvény a mikroszekundumok levágásához."""
        return timedelta(seconds=int(td.total_seconds()))
    @property
    def ElapsedTime(self) -> timedelta:        
        return self._strip_ms(self.ElapsedTimeu)
    @property
    def ExpectedTime(self) -> timedelta:
        return self._strip_ms(self.ExpectedTimeu)
    @property
    def DeltaTime(self) -> timedelta:
        return self._strip_ms(self.DeltaTimeu)
    @property
    def ElapsedTimeS(self) -> float:
        return self.ElapsedTimeu.total_seconds()
    @property
    def ExpectedTimeS(self) -> float:
        return self.ExpectedTimeu.total_seconds()
    @property
    def DeltaTimeS(self) -> float:
        return self.DeltaTimeu.total_seconds()

listener: Listener

# ==============================================================================
# 💿️ Lemez kezelő eljárások
# ==============================================================================

def BytesX(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'kilo', 2: 'mega', 3: 'giga', 4: 'tera'}
    pls={0 : 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n]+'bytes', pls[n], n
def BytesS(size):
    a,b,c,d=BytesX(size)
    return f"{a:.2f} {c}"

# ==============================================================================
# 💿💬 Lemez cimke, S# olvasás
# ==============================================================================

@dataclass
class cDisk:
    SN: str=""
    ID: str=""
    Drive: str=""
    Media: str=""
    SectorsOfDisk: int=0
    SectorsOfPrt: int=0
    BytesPSector: int=0
    Size: int=0
    Free: int=0
    IntTyp: str=""
    _ByteFields={'Size','Free'}
    def s(self) -> str:
        sorok=["--- Disk Adatlap --- "]
        elv={' ',',','.',';','_','-'} # elválasztók

        for field in fields(self):
            ertek=getattr(self,field.name)

            if isinstance(ertek,str):
                VnElv = bool(set(ertek) & elv)
                if len(ertek) > 8 and not VnElv:
                    ertek = " ".join([ertek[i:i+4] for i in range(0, len(ertek), 4)])
                pass
            if isinstance(ertek,(int,float)): # float esetében kerekítés átgondolandó
                if field.name in self._ByteFields:
                    ertek=BytesS(ertek)
                else:
                    ertek = f"{ertek:_}".replace("_", " ")
                pass
            sorok.append(f"{field.name:<20}: {ertek}")
        return "\n".join(sorok)

def gDiskProps():
    #region Logika
    # lekérjük a lemez adatait: Gyáriszám, sectorokszáma, köteg cimkéje.
    # USB-re csatolt merevlemez adatait igyekszünk lekérni.
    #  Ha több van csatolva, akkor bajban vagyunk...
    #  Lehet paraméterezni is kellene? Ha van paraméter,
    #  akkor azt a drive-t olvassuk be.
    # Tehát nem a PenDrive-t
    #endregion
    
    #region 🛠️ PARAMÉTEREK BEÁLLÍTÁSA
    # Ezek a paraméterek csak ehhez a funkcióhoz kellenek,
    #  ezért nem a fő paraméterek között vannak
    #endregion
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
        #prt=None
        #iMaxPSz=0
        #iMaxLSz=0
        rDisk=cDisk()        
        for PDisk in MSFT_PDs:
            # print('Fnd:', PDisk)
            #v_PD_Name=PDisk.FriendlyName

            sDrvID=getattr(PDisk,'DeviceID', None)
            if sDrvID is None: continue

            DDs=WMIcm2.Win32_DiskDrive(Index=sDrvID)
            if not DDs: continue
            DD=DDs[0] # Feltételezhetően csak egy van
            
            for DP in DD.associators(wmi_result_class="Win32_DiskPartition"):
                #if iMaxSz<DP.Size:
                #    iMaxSz=DP.Size
                for DL in DP.associators(wmi_result_class="Win32_LogicalDisk"):
                    if rDisk.Size<int(DL.Size):
                        rDisk.Size=DL.Size
                        rDisk.Free=DL.FreeSpace
                        rDisk.ID=DL.VolumeName
                        rDisk.Drive=DL.Caption
                        rDisk.BytesPSector=DD.BytesPerSector                        
                        rDisk.SectorsOfPrt=DD.TotalSectors
                        rDisk.SN=DD.SerialNumber
                        rDisk.Media=DD.MediaType
                        rDisk.IntTyp=DD.InterfaceType
                        rDisk.SectorsOfDisk=int(PDisk.Size)//int(PDisk.LogicalSectorSize)
            DDs=None
        if rDisk.Size==0:return "No drive"    
        #prt={"S#":iPDSN, "ID":iLabel, "Drv":iDrLt, "Media":iMdTp, "Sct":ilSctN # pyright: ignore[reportPossiblyUnboundVariable]
        #     , "BPSct":ilSctS,"Size":iMaxLSz,"Free":iFree,"IntTp":iIntTp,"FSct":iSct} # pyright: ignore[reportPossiblyUnboundVariable]
        return rDisk
    except Exception as e:
        return f"Kritikus hiba a WMI lekérdezés során: {e}"
    finally:
        MSFT_PDs=None
        if "WMIcm2" in locals():
            del WMIcm2 # pyright: ignore[reportPossiblyUnboundVariable]
        if "WMIstr" in locals():
            del WMIstr # pyright: ignore[reportPossiblyUnboundVariable]
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
    #DBG print(f"[{'INIT'.center(6)}] Keresés: '{wTitle}' ablak...")

    try:
        # Kapcsolódás a 'DiskFresh' ablakhoz címrészlet alapján

        #Debug
        #DBG print('App_Tmp:',wTitle)
        with warnings.catch_warnings(): # disable admin warning
            warnings.simplefilter("ignore")
            app = Application(backend="win32").connect(
                # Ouch... ha fut, akkor wTitle nem jó... akkor a Refreshing-re kellene keresni
                title_re=f".*{wTitle}.*"
                ,class_name="#32770"
                #,path=r"C:\Program Files\DiskFresh\DiskFresh.exe"
            )
            #Debug
            #DBG print('AppTxt:',app.window_text())        
        
        # ==============================================================================
        # 🗔
        # ==============================================================================
        # Lekérjük a főablak objektumát
        owDiskFresh = app.top_window()
        # Debug
        #DBG print('Window:',owDiskFresh.window_text())
        #DBG print('WinClass:', owDiskFresh.class_name())
        
        # ==============================================================================
        # ▭
        # ==============================================================================
        # Lekérjük a Static vezérlőt ID alapján
        oLabel = owDiskFresh.child_window(control_id=wLabelID, class_name="Static")
        
        #DBG print(f"[{'INIT'.center(6)}] ✅ Sikeresen inicializálva a vezérlő (ID: {wLabelID}).")
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
    #global sStop
    vRes=""

    def waitFn():
        global sStop
        nonlocal vRes
        vRes=oLabel.window_text()
        return sStop or vRes!=vText
    
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
                , func=waitFn
                #, func=lambda: (((vRes:=oLabel.window_text()) and 0) or vRes!= vText)
                #, func=lambda: vRes:=sStop or (oLabel.window_text() != vText)
            )            
            
            #DBG print(f"[{'CHECK'.center(6)}] ✅ Ablak aktív. Aktuális szöveg: **{vRes}**")
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
    if sv[-8:]==" TimeOut": # right(sv,7)="TimeOut"
        sv=sv[:-8]
        vDT=vDT-timedelta(seconds=10) # 10 sec is the timeout        
    
    # Ha nem adat van, akkor a szöveget küldi vissza.
    if len(lSV)>3:
        if lSV[0].isdigit() and lSV[3].isdigit():
            return cLog(vDT,int(lSV[0]),int(lSV[3]))
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

def calcTimes(SV:cLog,pSV:cLog,tStart:datetime):
    rCalc=cCalc()
    if SV.Akt!=-1 and pSV.Akt!=-1 and not tStart is None:
        rCalc.Percent=1.0*SV.Akt/SV.length # vPrc
        rCalc.ElapsedTimeu=SV.TimeStamp-tStart # Eltelt idő vTE
        rCalc.DeltaTimeu=SV.TimeStamp-pSV.TimeStamp # vDT
        rCalc.DeltaSectors=SV.Akt-pSV.Akt # vDS
        rCalc.TimeAktPrc=1.0*rCalc.DeltaTimeu/rCalc.ElapsedTimeu # Időköz jelenszázalék vDTvp
        rCalc.SectorAktPrc=1.0*rCalc.DeltaSectors/SV.Akt # SV.Akt=vSE vDSvp
        rCalc.TimeDPrc=rCalc.TimeAktPrc/rCalc.Percent # Jelen/percent=teljes vDTp
        rCalc.SectorDPrc=1.0*rCalc.DeltaSectors/SV.length # Sectorköz százalék vDSp
        # Hátra lévő idő
        rCalc.ExpectedTimeu=(SV.length-SV.Akt)*rCalc.DeltaTimeu/rCalc.DeltaSectors # vTH
        rCalc.Far=min(rCalc.ElapsedTimeS,rCalc.ExpectedTimeS) # vT
        rCalc.TimePSectors=1024**2*rCalc.DeltaTimeS/rCalc.DeltaSectors # vTpS
        vSpT=84.375*rCalc.DeltaSectors/(rCalc.DeltaTimeS*(1024**2))
        #vSpT=1.0/vTpS
        '''
        vRes={"ElapsedTime":vTE-timedelta(microseconds=vTE.microseconds)
            ,"ExpectedTime":vTH-timedelta(microseconds=vTH.microseconds)
            ,"Far":vT # -microseconds, hogy tiszta legyen a kimenet
            ,"DeltaTime":vDT
            ,"DeltaSectors":vDS
            ,"TpS":vTpS
            ,"SpT":vSpT}
        return vRes
        '''
    return rCalc
    pass # calcTimes

# ==============================================================================
# 💿🖋 Lemez frissítés Monitorozása
# ==============================================================================

#region Működés
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
#endregion

# ==============================================================================
# 🧐⌨
# ==============================================================================

def on_press(key: Union[Key, KeyCode, None]) -> None:
    global sStop
    if key == Key.esc or (isinstance(key, KeyCode) and not key.char is None and key.char.lower() == 'q'):
        evPeriod.set() # Azonnal felébreszti a wait()-et
        sStop=True # Azonnal leállítja az wait_untilt.
        #return False

# Fő program inicializálása
def init():
    global sStop
    sStop=False
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
    vDP=gDiskProps()
    #vDP="Test"

    if not isinstance(vDP, cDisk):
        print("Disk props:", vDP)
        print(" ❌ vDP is not cDisk")
        return False
    else:
        print("Disk props:", vDP.s())
    #DBG print("vDP arrived")
    #return

    #region Mely adatok vannak meg,
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
    #endregion


    #region Státusz bárt megkeresni a DiskFresh alkalmazáson.
    # ? Pontosabban megvárni, hogy meglegyen az alkalmazás...

    # Egyenlőre nem várunk, ha nem fut a program, kilépünk...
    #endregion

    # debug
    #DBG print("Get_WinDiskFresh")

    if not getwDiskFresh():
        #DBG print("No DiskFresh launched") # Kiírja a rutin eleve
        return False
    #DBG print("Hmmm")

    #region Program inicializálva
    #  A ciklus jön, mely ellenőrzi a státus sor értékét, és logolja
    #  A program futása közben, bármikor ki lehessen lépni a Q, Esc billentyűkkel.
    #    A ciklustól függetlenül lehessen lőni logot.
    #    ? A ciklust újraütemezve lehessen lőni logot.
    #       (pl. 05 kor indítottam a mérést, de egészkor akarom az órás logookat)
    # hm.. Lehessen átkapcsolni a logolást, hogy ne a kezdéshez,
    #  hanem az órához igazodjon a mérés ütemezése.
    #endregion

    #sStop=False
    tBegin="Not Running"
    tEnd="Finished" # Nem biztos, hogy ez a szöveg!

    
    global vFigyel
    #vStart=True
    #!!! Nem vStart, hanem vState 
    # 0-Start, 
    # 1, begin measure, 
    # 2 measure, 
    # 3 final, 
    # 4 stop
    vState=0
    v_TimeSt=None # a sectorok mérésének kezdő indőpontja
    iTime=datetime.now()
    vHtr=0
    vSVe=cLog()
    
    #DBG print("While")
    # részletesen: file://./diskfreshmon.md#figyelő-ciklus
    while not sStop:
        # logolás
        # Kell az aktuális idő
        jTime=datetime.now()
        # és mért adat, mely akár 10 másodpercig is várhat
        vSV=getAktVal()

        #region DBG vSV.pr
        if isinstance(vSV, cLog):
            print(f" 👓︎ Figyelt: {vSV.TimeStamp.__format__("%y%m%d_%H%M%S")} Akt: {vSV.Akt} Full: {vSV.length}")
        else:
            print(f" 👓︎ Figyelt:  {vSV}") #,vSV)
        #endregion

        '''
        if vSV==tBegin: # még nem indult el. Kell alapozni?
            # Olvasási Timeout átállítása nagyra, had várja míg elindul
            #DBG print("Long wait")
            #vFigyel=4 # 15p
            #print(f"\nSzint: {vFigyel}\nCh: {lFigyelő[vFigyel].check} Pr: {lFigyelő[vFigyel].period} Ln: {lFigyelő[vFigyel].length}")
            pass
        '''
        if vSV==tEnd: # elkészült, de teljesen
            #hmm úgy tűnik, a végén üres szöveget ad a státuszsor
            break
        if isinstance(vSV, cLog): # adat!
            #if vStart: # léptetni az állapotjelzőt
            #    vStart=False
            if vState==0: # léptetni az állapotjelzőt
                vState=1 # Begin Measure
                # akkor lesz 2-ő, ha már van előző érték is.
                # Vagy ha megjött a 0.szektor?
            # Nem itt kellene a határértéket ellenőrizni, mert azt az előzőből számoltuk
            '''
            if vHtr<=0:
                # Elérte a határidőt, logolni kellene
                print(f"\nlog: TS: {vSV.TimeStamp:%y-%m-%d %H:%M:%S.%f} Akt.: {vSV.Akt:_} Telj.: {vSV.length:_}\n")
                iTime=datetime.now()
            '''
                
            # ha elötte "indult", akkor a timeout visszaállítása gyorsra.
            #  Ne várjon akármeddig, mert kell a rész adat is
            
            # Figyelem! ez nem biztos, hogy logolandó...
            # Ellenőrizni kell a folyamat helyzetét, és ha szükséges váltani a
            #  Mélységet

            # a vSVe tárolja az előző adatot.
            # Ebből kiszámolhatjuk az aktuális "sebességet", időt, stb.

            if (vSVe.Akt!=-1) or (vSV.Akt!=vSVe.Akt): # van előző érték, tudjuk számolni a sebességet.
                if vSVe.Akt==-1: 
                    # Elvileg ez a kezdés... le kéne menteni...
                    # a kezdés idejét
                    # illetve logolni, hogy elkezdtük...
                    # akkor most itt, vagy vSV.Akt=0 a kezdés?
                    # DBG pr
                    print("Nincs előző vSV")                    
                    vFigyel=0 # nagyon figyeljünk, mikor jön következő érték!
                    print(f"\nSzint: {vFigyel}\nCh: {lFigyelő[vFigyel].check} Pr: {lFigyelő[vFigyel].period} Ln: {lFigyelő[vFigyel].length}")
                    if vSV.Akt==0: # nem csak hogy van adat, de ez az nulladik szektor.
                        print("0. sector!") #Dbg
                        
                        v_TimeSt=vSV.TimeStamp # Az kezddet időpontja
                        iTime=v_TimeSt # a periódus kezdeti idejét beállítjuk
                        print("Kezdés: ",v_TimeSt) #Dbg
                        # ekkor még nincs előző adat!
                        # logolást ne felejtsük!
                        pass # 0. szektor!
                    # Figyelem! ha az első adat nem 0, akkor el sem tudunk indulni!
                    pass # nincs előző érték
                elif not v_TimeSt is None: # ha megvan a kezdés időpontja és van előző adat
                    if vState==1:
                        vState=2
                    # van előző érték, tudjuk számolni a sebességet.
                    # kell a kezdési idő
                    # (vSV.TimeStamp-vSVe.TimeStamp) st/r H/t-r H=st*(t-r)/r
                    # (vSv.Akt-vSVe.Akt)
                    # H=(vSV.TimeStamp-vSVe.TimeStamp)*(1/(vSv.Akt-vSVe.Akt)-1)
                    # vVég=vSV.TimeStamp+H
                    # és kell a várható végső idő
                    #DBG print("Van előző vSV")
                    #DBG print("TS",v_TimeSt)
                    dcSV:cCalc=calcTimes(vSV,vSVe,v_TimeSt)
                    print(f" 🧐➗ calc: %: {dcSV.Percent:.1f} eddig: {dcSV.ElapsedTime} hátra:{dcSV.ExpectedTime} Sebesség:{dcSV.SectorsPTime:.2f}")
                    #vTE=vSV.TimeStamp-v_TimeSt # Eltelt idő
                    #vDT=vSV.TimeStamp-vSVe.TimeStamp
                    #vDS=vSV.Akt-vSVe.Akt
                    ## Hátra lévő idő
                    #vTH=(vSV.length-vSV.Akt)*vDT/vDS
                    #vT=min(vTE,vTH)
                    if vFigyel+1<lFigyelőc and dcSV.Far>lFigyelő[vFigyel].length:
                        vFigyel+=1
                        print(f"\nSzint: {vFigyel}\nCh: {lFigyelő[vFigyel].check} Pr: {lFigyelő[vFigyel].period} Ln: {lFigyelő[vFigyel].length}")
                    elif vFigyel>0 and dcSV.Far<lFigyelő[vFigyel-1].length:
                        vFigyel-=1
                        print(f"\nSzint: {vFigyel}\nCh: {lFigyelő[vFigyel].check} Pr: {lFigyelő[vFigyel].period} Ln: {lFigyelő[vFigyel].length}")
                    vHtr=(lFigyelő[vFigyel].period # periódus idő
                        -(iTime-datetime.now()).total_seconds()) # letelt idő
                    #iTime+lFigyelő[vFigyel].period: Periódus lejárta
                    if vHtr<=0: # ha lejárt, akkor logolunk
                        print(f"\nlog: TS: {vSV.TimeStamp:%y-%m-%d %H:%M:%S.%f} Akt.: {vSV.Akt:_} Telj.: {vSV.length:_}\n")
                        vHtr=lFigyelő[vFigyel].period
                        iTime=datetime.now()
                        # vagy v_TimeSt-tól számított periódus idő mostanig
                        # iTime=v_TimeSt+timedelta(seconds=(datetime.now()-v_TimeSt).total_seconds()//vHtr*vHtr)
                        # vagy éjféltől számított
                        #iTime=timedelta(seconds=((n:=datetime.now())-(m:=n.replace(hour=0, minute=0,second=0,microsecond=0))).total_seconds()//vHtr*vHtr)+m
                        '''
                        n=datetime.now() # Most
                        m=n.replace(hour=0, minute=0,second=0,microsecond=0) # éjfél
                        iTime=m+timedelta(seconds=((n-m).total_seconds()//vHtr*vHtr)) # éjfél + másodpercek perióduskezdetig
                        '''
                        pass # periódus lejárt



                    print(f"Várakozás: {min(
                        lFigyelő[vFigyel].check # ellenörző idő
                        ,vHtr)}") # Periódus időig hátra levő idő
                    if vHtr>0.1: # csak akkor várjunk, ha van mit várni
                        if evPeriod.wait(timeout=min(

                            lFigyelő[vFigyel].check # ellenörző idő
                            ,vHtr # Periódus időig hátra levő idő

                            )): # Vár ellenörzés időt, de a periódusig.
                            break # esemény kezelés gombnyomásra (most csak leáll)

                    pass # van előző adat! ki: dcSV!! statisztika

                #DBG print("vSV mentés")
                #vSVe=replace(vSV)
                vSVe=vSV # elég átcimkézni, mert vSV új objektumot kap.

                pass # van új adat
            
            pass # Adat!
        
        # itt a folyamat mélységétől függ, meddig várjon.
        #  indulási állapotban várni 600-at (10p)
        #  Várni a periódus 20-adával,
        #  illetve ha a periódusig kevesebb az idő mint a huszada, akkor annyival.
        # Csak, de csak akkor várjunk hosszan, ha nem kell az indulásra figyelnünk!
        #if not vSV==tBegin
        # Ejch... a lassu winyón kb 1 sec a változás... 
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

