#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-107: bygger korpusen ur tillverkarnas publicerade datablad.

Varje rad i KALLOR nedan ar EN uppgift ur ETT dokument, och skriptet gor tre
saker med den:

  1. hamtar dokumentet EN gang och cachar ravyten under sin sha256
  2. letar upp citatet ORDAGRANT i den normaliserade dokumenttexten
  3. konstruerar en `Uppgift`, vilket kor enhetsgrinden

Steg 3 ar det som gor korpusen vard nagot. Skriptet kan inte skriva in en enhet
som dokumentet inte bar: `Uppgift.__post_init__` kraver att talet och enheten
star bredvid varandra i citatet, eller - for tabeller vars enhet star i
rubriken - att den positionella kolumnlasningen stammer mot bade rubrik och
rad. Ett citat som inte gar att hitta i dokumentet stoppar bygget.

Nataviserat och artigt: en URL hamtas EN gang och ligger sedan i
`data/tillverkardatablad/cache/`. Kor med

    nice -n 19 ionice -c3 python3 tests/protocol/kor_m107_bygg_korpus.py

VAD SOM INTE GICK, OCH VARFOR DET STAR HAR
------------------------------------------
`ej_belagda` ar inte en restpost. Den ar mätningens andra halva: en komponent
utan datablad ska sta som `saknas` med ETT SKAL, aldrig fyllas med en grannes
tal. Tre klasser av skal star i tabellen nedan, alla uppmatta:

  * tillverkaren har tagit bort modellen ur sitt publika dokumentindex
    (KUKA KR 10 R1100 sixx och KR 210 R2700 extra)
  * dokumentet finns men utdragningen flatar samman kolumnerna sa att varken
    par- eller kolumngrinden kan verifiera talet mot enheten
    (FANUC M-710iC/50: "50 show kg", "2050 mmspace")
  * tillverkaren publicerar en ANNAN storhet an den vi fragade om
    (ABB IRB 360-1/1130: 1130 mm ar en DIAMETER, inte en rackvidd)
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Varje tal i tillverkarkorpusen star ordagrant i tillverkarens eget "
        "publicerade datablad med sin enhet bredvid sig, och en komponent "
        "utan datablad star som saknad med ett skal i stallet for att fyllas "
        "med en grannes tal.",
    "under_prov": ("svc/vc_assist_svc/tillverkardatablad.py",),
    "facit":
        "tillverkarens publicerade dokument: citatet ska ga att hitta "
        "ORDAGRANT i den normaliserade dokumenttexten, och talet ska sta "
        "bredvid sin enhet i citatet eller stamma mot bade rubrik och rad i "
        "den positionella kolumnlasningen",
    "facitkalla":
        "tillverkarnas egna publicerade datablad (ABB, KUKA, FANUC med "
        "flera), hamtade en gang och cachade under sin sha256 i "
        "data/tillverkardatablad/cache/. Dokumenten ar skrivna av nagon annan "
        "an oss och kan inte bara var egen missuppfattning.",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "ett citat som inte gar att hitta i dokumentet stoppar bygget",
        "ett tal utan sin enhet bredvid sig i citatet avvisas av "
        "Uppgift.__post_init__",
        "en komponent utan datablad ska sta som saknad med ETT skal, aldrig "
        "fyllas med en grannes tal",
        "ett dokument som publicerar en ANNAN storhet an den vi fragade om "
        "(en diameter i stallet for en rackvidd) far inte raknas som belagt",
    ),
    "kraver": ("inget",),
    "matningar": ("M-107",),
}

import json
import os
import re
import sys

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
sys.path.insert(0, os.path.join(ROT, "svc"))

from vc_assist_svc import tillverkardatablad as TD          # noqa: E402

# Hur mycket text runt citatet som lagras som `utdrag`. Utdraget ar det som
# gor att korpusgrinden kan kora utan natet: citatet ska sta i utdraget, och
# utdraget i dokumentet.
UTDRAG = 180

# --- ABB -------------------------------------------------------------------

ABB_1200 = ("https://library.e.abb.com/public/6f866d55894a49a7b44384db76e01b4b/"
            "IRB1200_ROB0275EN_A.pdf")
ABB_2600 = ("https://library.e.abb.com/public/b158e2dcf8cc41b4a724eda1e22f87fb/"
            "3HAC035959%20PS%20IRB%202600%20on%20IRC5-en.pdf")
ABB_4600 = ("https://library.e.abb.com/public/7f776502855949bba39e2105e6d70209/"
            "IRB%204600_DATASHEET.pdf")
ABB_6700 = ("https://library.e.abb.com/public/a2698bc8d34a36a048257d4000330712/"
            "IRB_6700_EN.pdf")
ABB_660 = ("https://library.e.abb.com/public/bb6f658190ee693bc1257b28005760dc/"
           "IRB660_PR10284EN_D_HR.pdf")
ABB_360 = ("https://library.e.abb.com/public/1c971fb90d8c34f8c1257c2100468677/"
           "ROB0082EN_F_HR.pdf")
ABB_910 = ("https://library.e.abb.com/public/2ac1d57a1bf4431391aa558f27c99cf5/"
           "IRB910SC-revF-9AKK106713A1510.pdf")

# --- FANUC / UR / Yaskawa --------------------------------------------------

FANUC_LRM7L = ("https://www.fanucamerica.com/docs/default-source/robotics-files/"
               "lr-mate/lr-mate-200id-7l-data-sheet.pdf")
FANUC_M10ID12 = ("https://www.fanucamerica.com/docs/default-source/"
                 "fanuc-robot-datasheets-new/flyer-m-10id-12-en.pdf")
FANUC_M710IC50 = ("https://www.fanucamerica.com/docs/default-source/robotics-files/"
                  "fanuc-robot-datasheets-new/datasheet-m-710ic-50.pdf")
UR10E = ("https://www.universal-robots.com/manuals/EN/DataSheets/"
         "UR10e_techsheet_pdf_online/UR10e_techsheet_en.pdf")
UR5E = ("https://www.universal-robots.com/manuals/EN/DataSheets/"
        "UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf")
UR16E = ("https://www.universal-robots.com/manuals/EN/DataSheets/"
         "UR16e_techsheet_pdf_online/UR16e_techsheet_en.pdf")
YASKAWA_GP = ("https://www.motoman.com/getmedia/"
              "1a40ce78-99c3-4e43-bbce-b9318263f464/GP7_GP8.pdf.aspx")


def _kol(rubrik, rad, modell, i):
    return {"rubrik": rubrik, "rad": rad, "modell_i_rad": modell, "index": i}


# Rubriken i ABB:s produktspecifikation for IRB 2600. Enheterna star DAR och
# inte bredvid talen, och det ar precis darfor lasningen ar positionell.
R2600 = r"Robot variant Handling capacity \(kg\) Reach \(m\)"


KALLOR = [
    # ---------------- ABB IRB 1200 ----------------
    # Ordagranna par: ABB skriver "901mm" och "5kg" utan mellanslag.
    dict(modell="ABB IRB 1200-5/0.9", tillverkare="ABB",
         vc_namn=["IRB 1200-5/0.9"], bank_uri="bank://robot/abb_irb_1200_5_0900",
         url=ABB_1200,
         uppgifter={
             "rackvidd": dict(varde=901, enhet="mm",
                              citat=r"IRB 1200-5/0\.9 901mm 5kg 0\.3kg"),
             "nyttolast": dict(varde=5, enhet="kg",
                               citat=r"IRB 1200-5/0\.9 901mm 5kg"),
         },
         ej_belagda={
             "repeterbarhet": "ROB0275EN_A skriver ingen repeterbarhet per "
                              "variant; bladet ar ett saljblad, inte "
                              "produktspecifikationen.",
             "vikt": "bladet skriver 'Weight 52 KG / 54 KG' i tva kolumner "
                     "utan att raden sager vilken kolumn som ar vilken variant.",
             "diameter": "ABB anger rackvidd for IRB 1200, inte diameter.",
         }),
    dict(modell="ABB IRB 1200-7/0.7", tillverkare="ABB",
         vc_namn=["IRB 1200-7/0.7"], bank_uri="bank://robot/abb_irb_1200_7_0700",
         url=ABB_1200,
         uppgifter={
             "rackvidd": dict(varde=703, enhet="mm",
                              citat=r"IRB 1200-7/0\.7 703mm 7kg 0\.3kg"),
             "nyttolast": dict(varde=7, enhet="kg",
                               citat=r"IRB 1200-7/0\.7 703mm 7kg"),
         },
         ej_belagda={
             "repeterbarhet": "se IRB 1200-5/0.9: bladet bar ingen "
                              "repeterbarhet per variant.",
             "vikt": "se IRB 1200-5/0.9: viktkolumnerna ar inte radbundna.",
             "diameter": "ABB anger rackvidd for IRB 1200, inte diameter.",
         }),

    # ---------------- ABB IRB 2600: enheten star i RUBRIKEN ----------------
    dict(modell="ABB IRB 2600-20/1.65", tillverkare="ABB",
         vc_namn=["IRB 2600-20/1.65"], bank_uri="bank://robot/abb_irb_2600_20_1650",
         url=ABB_2600,
         uppgifter={
             "nyttolast": dict(varde=20, enhet="kg",
                               citat=R2600 + r" IRB 2600-20/1\.65 20 1\.65",
                               kolumn=_kol("Robot variant Handling capacity (kg) "
                                           "Reach (m)", "IRB 2600-20/1.65 20 1.65",
                                           "IRB 2600-20/1.65", 0)),
             "rackvidd": dict(varde=1.65, enhet="m",
                              citat=R2600 + r" IRB 2600-20/1\.65 20 1\.65",
                              kolumn=_kol("Robot variant Handling capacity (kg) "
                                          "Reach (m)", "IRB 2600-20/1.65 20 1.65",
                                          "IRB 2600-20/1.65", 1)),
         },
         ej_belagda={
             "repeterbarhet": "3HAC035959 anger 0.04 mm i en kolumntabell vars "
                              "rubrikrad utdragningen bryter isar; kolumngrinden "
                              "kan inte binda talet till varianten.",
             "vikt": "vikten star inte per variant i den lasta tabellen.",
             "diameter": "ABB anger rackvidd for IRB 2600, inte diameter.",
         }),
    dict(modell="ABB IRB 2600-12/1.65", tillverkare="ABB",
         vc_namn=["IRB 2600-12/1.65"], url=ABB_2600,
         uppgifter={
             "nyttolast": dict(varde=12, enhet="kg",
                               citat=R2600 + r".{0,40}?IRB 2600-12/1\.65 12 1\.65",
                               kolumn=_kol("Robot variant Handling capacity (kg) "
                                           "Reach (m)", "IRB 2600-12/1.65 12 1.65",
                                           "IRB 2600-12/1.65", 0)),
             "rackvidd": dict(varde=1.65, enhet="m",
                              citat=R2600 + r".{0,40}?IRB 2600-12/1\.65 12 1\.65",
                              kolumn=_kol("Robot variant Handling capacity (kg) "
                                          "Reach (m)", "IRB 2600-12/1.65 12 1.65",
                                          "IRB 2600-12/1.65", 1)),
         },
         ej_belagda={"repeterbarhet": "se IRB 2600-20/1.65.",
                     "vikt": "se IRB 2600-20/1.65.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    dict(modell="ABB IRB 2600-12/1.85", tillverkare="ABB",
         vc_namn=["IRB 2600-12/1.85"], url=ABB_2600,
         uppgifter={
             "nyttolast": dict(varde=12, enhet="kg",
                               citat=R2600 + r".{0,80}?IRB 2600-12/1\.85 12 1\.85",
                               kolumn=_kol("Robot variant Handling capacity (kg) "
                                           "Reach (m)", "IRB 2600-12/1.85 12 1.85",
                                           "IRB 2600-12/1.85", 0)),
             "rackvidd": dict(varde=1.85, enhet="m",
                              citat=R2600 + r".{0,80}?IRB 2600-12/1\.85 12 1\.85",
                              kolumn=_kol("Robot variant Handling capacity (kg) "
                                          "Reach (m)", "IRB 2600-12/1.85 12 1.85",
                                          "IRB 2600-12/1.85", 1)),
         },
         ej_belagda={"repeterbarhet": "se IRB 2600-20/1.65.",
                     "vikt": "se IRB 2600-20/1.65.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    dict(modell="ABB IRB 2600ID-15/1.85", tillverkare="ABB",
         vc_namn=["IRB 2600ID-15/1.85"], url=ABB_2600,
         uppgifter={
             "nyttolast": dict(varde=15, enhet="kg",
                               citat=R2600 + r".{0,120}?IRB 2600ID-15/1\.85 15 1\.85",
                               kolumn=_kol("Robot variant Handling capacity (kg) "
                                           "Reach (m)", "IRB 2600ID-15/1.85 15 1.85",
                                           "IRB 2600ID-15/1.85", 0)),
             "rackvidd": dict(varde=1.85, enhet="m",
                              citat=R2600 + r".{0,120}?IRB 2600ID-15/1\.85 15 1\.85",
                              kolumn=_kol("Robot variant Handling capacity (kg) "
                                          "Reach (m)", "IRB 2600ID-15/1.85 15 1.85",
                                          "IRB 2600ID-15/1.85", 1)),
         },
         ej_belagda={"repeterbarhet": "se IRB 2600-20/1.65.",
                     "vikt": "se IRB 2600-20/1.65.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    # OBS namnskillnaden: databladet skriver 2.00, biblioteket 2.0. Det ar
    # samma robot, och det ar just darfor `vc_namn` skrivs ut ORDAGRANT som
    # biblioteket stavar den i stallet for att matchas fram.
    dict(modell="ABB IRB 2600ID-8/2.00", tillverkare="ABB",
         vc_namn=["IRB 2600ID-8/2.0"], url=ABB_2600,
         uppgifter={
             "nyttolast": dict(varde=8, enhet="kg",
                               citat=R2600 + r".{0,160}?IRB 2600ID-8/2\.00 8 2\.00",
                               kolumn=_kol("Robot variant Handling capacity (kg) "
                                           "Reach (m)", "IRB 2600ID-8/2.00 8 2.00",
                                           "IRB 2600ID-8/2.00", 0)),
             "rackvidd": dict(varde=2.00, enhet="m",
                              citat=R2600 + r".{0,160}?IRB 2600ID-8/2\.00 8 2\.00",
                              kolumn=_kol("Robot variant Handling capacity (kg) "
                                          "Reach (m)", "IRB 2600ID-8/2.00 8 2.00",
                                          "IRB 2600ID-8/2.00", 1)),
         },
         ej_belagda={"repeterbarhet": "se IRB 2600-20/1.65.",
                     "vikt": "se IRB 2600-20/1.65.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),

    # ---------------- ABB IRB 4600 (italienskt datablad) ----------------
    # Kallan ar pa italienska. Det spelar ingen roll for enheten: "2.05 m" och
    # "60 kg" ar samma tecken pa alla sprak, och citatet star ordagrant.
    dict(modell="ABB IRB 4600-60/2.05", tillverkare="ABB",
         vc_namn=["IRB 4600-60/2.05"], bank_uri="bank://robot/abb_irb_4600_60_2050",
         url=ABB_4600,
         uppgifter={
             "rackvidd": dict(varde=2.05, enhet="m",
                              citat=r"IRB 4600-60/2\.05 2\.05 m 60 kg"),
             "nyttolast": dict(varde=60, enhet="kg",
                               citat=r"IRB 4600-60/2\.05 2\.05 m 60 kg"),
         },
         ej_belagda={
             "repeterbarhet": "bladet anger 0.05 - 0.06 mm som ETT INTERVALL "
                              "over alla varianter, inte ett varde for den har.",
             "vikt": "bladet anger 'Peso robot da 412 a 435 kg' - ett intervall "
                     "over familjen, inte variantens vikt.",
             "diameter": "ABB anger rackvidd (sbraccio), inte diameter.",
         }),
    dict(modell="ABB IRB 4600-45/2.05", tillverkare="ABB",
         vc_namn=["IRB 4600-45/2.05"], url=ABB_4600,
         uppgifter={
             "rackvidd": dict(varde=2.05, enhet="m",
                              citat=r"IRB 4600-45/2\.05 2\.05 m 45 kg"),
             "nyttolast": dict(varde=45, enhet="kg",
                               citat=r"IRB 4600-45/2\.05 2\.05 m 45 kg"),
         },
         ej_belagda={"repeterbarhet": "se IRB 4600-60/2.05: intervall.",
                     "vikt": "se IRB 4600-60/2.05: intervall.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    dict(modell="ABB IRB 4600-40/2.55", tillverkare="ABB",
         vc_namn=["IRB 4600-40/2.55"], url=ABB_4600,
         uppgifter={
             "rackvidd": dict(varde=2.55, enhet="m",
                              citat=r"IRB 4600-40/2\.55 2\.55 m 40 kg"),
             "nyttolast": dict(varde=40, enhet="kg",
                               citat=r"IRB 4600-40/2\.55 2\.55 m 40 kg"),
         },
         ej_belagda={"repeterbarhet": "se IRB 4600-60/2.05: intervall.",
                     "vikt": "se IRB 4600-60/2.05: intervall.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    # Modellnamnet sager 2.50 och databladet sager 2.51 m. Talet ur kallan
    # galler; modellnamnet ar ett namn, inte ett matt.
    dict(modell="ABB IRB 4600-20/2.50", tillverkare="ABB",
         vc_namn=["IRB 4600-20/2.50"], url=ABB_4600,
         uppgifter={
             "rackvidd": dict(varde=2.51, enhet="m",
                              citat=r"IRB 4600-20/2\.50 2\.51 m 20 kg"),
             "nyttolast": dict(varde=20, enhet="kg",
                               citat=r"IRB 4600-20/2\.50 2\.51 m 20 kg"),
         },
         ej_belagda={"repeterbarhet": "se IRB 4600-60/2.05: intervall.",
                     "vikt": "se IRB 4600-60/2.05: intervall.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),

    # ---------------- ABB IRB 6700 ----------------
    dict(modell="ABB IRB 6700-235/2.65", tillverkare="ABB",
         vc_namn=["IRB 6700-235/2.65"], bank_uri="bank://robot/abb_irb_6700_235_2650",
         url=ABB_6700,
         uppgifter={
             "rackvidd": dict(varde=2.65, enhet="m",
                              citat=r"6700-235 2\.65 m 235 kg"),
             "nyttolast": dict(varde=235, enhet="kg",
                               citat=r"6700-235 2\.65 m 235 kg"),
         },
         ej_belagda={
             "repeterbarhet": "IRB_6700_EN ar ett saljblad och anger ingen "
                              "repeterbarhet.",
             "vikt": "bladet anger 'Weight 1250 - 1280 kg' for familjen, inte "
                     "for varianten.",
             "diameter": "ABB anger rackvidd, inte diameter.",
         }),
    dict(modell="ABB IRB 6700-205/2.80", tillverkare="ABB",
         vc_namn=["IRB 6700-205/2.80"], url=ABB_6700,
         uppgifter={
             "rackvidd": dict(varde=2.80, enhet="m",
                              citat=r"6700-205 2\.80 m 205 kg"),
             "nyttolast": dict(varde=205, enhet="kg",
                               citat=r"6700-205 2\.80 m 205 kg"),
         },
         ej_belagda={"repeterbarhet": "se IRB 6700-235/2.65: saljblad.",
                     "vikt": "se IRB 6700-235/2.65: familjeintervall.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),
    dict(modell="ABB IRB 6700-150/3.20", tillverkare="ABB",
         vc_namn=["IRB 6700-150/3.20"], url=ABB_6700,
         uppgifter={
             "rackvidd": dict(varde=3.20, enhet="m",
                              citat=r"6700-150 3\.20 m 150 kg"),
             "nyttolast": dict(varde=150, enhet="kg",
                               citat=r"6700-150 3\.20 m 150 kg"),
         },
         ej_belagda={"repeterbarhet": "se IRB 6700-235/2.65: saljblad.",
                     "vikt": "se IRB 6700-235/2.65: familjeintervall.",
                     "diameter": "ABB anger rackvidd, inte diameter."}),

    # ---------------- ABB IRB 660 ----------------
    # INGEN vc_namn. Biblioteket bar en komponent som heter "IRB 660" och
    # deklarerar MaxPayload 250 - alltsa -250/3.15-varianten, inte den banken
    # namnger. Att binda den till -180/3.15 hade varit att fylla en komponent
    # med en GRANNES tal, och det ar just det som ar forbjudet.
    dict(modell="ABB IRB 660-180/3.15", tillverkare="ABB",
         vc_namn=[], bank_uri="bank://robot/abb_irb_660_180_3150", url=ABB_660,
         uppgifter={
             "nyttolast": dict(varde=180, enhet="kg",
                               citat=r"660-180/3\.15 180 kg 3\.15 m"),
             "rackvidd": dict(varde=3.15, enhet="m",
                              citat=r"660-180/3\.15 180 kg 3\.15 m"),
         },
         ej_belagda={
             "repeterbarhet": "bladet anger 'Position repeatability 0.1 mm' for "
                              "IRB 660 som familj, utan att raden binder talet "
                              "till -180/3.15 eller -250/3.15.",
             "vikt": "bladet anger ingen vikt.",
             "diameter": "ABB anger rackvidd, inte diameter.",
         },
         not_="Biblioteket bar 'IRB 660' med MaxPayload 250, alltsa den ANDRA "
              "varianten. Ingen vc_namn-bindning."),

    # ---------------- ABB IRB 360 FlexPicker: DIAMETER, inte rackvidd -------
    dict(modell="ABB IRB 360-1/1130", tillverkare="ABB",
         vc_namn=[], bank_uri="bank://robot/abb_irb_360_1_1130", url=ABB_360,
         uppgifter={
             "nyttolast": dict(varde=1, enhet="kg",
                               citat=r"IRB 360-1/1130 \* 1 kg 1130 mm"),
             "diameter": dict(varde=1130, enhet="mm",
                              citat=r"IRB 360-1/1130 \* 1 kg 1130 mm"),
         },
         ej_belagda={
             "rackvidd": "ABB publicerar 1130 mm under rubriken DIAMETER, inte "
                         "Reach. Bankens 565 mm ar 1130/2 - en rakning pa ett "
                         "publicerat tal, inte ett publicerat tal, och den star "
                         "stamplad PUBLICERAD_SPEC.",
             "repeterbarhet": "bladet anger 0.1 mm for IRB 360 som familj, inte "
                              "per variant.",
             "vikt": "bladet anger ingen vikt per variant.",
         },
         not_="Modellen finns inte i det installerade biblioteket; dar finns "
              "-3/1130, -8/1130, -1/1600 och -6/1600."),
    dict(modell="ABB IRB 360-3/1130", tillverkare="ABB",
         vc_namn=["IRB 360-3/1130"], url=ABB_360,
         uppgifter={
             "nyttolast": dict(varde=3, enhet="kg",
                               citat=r"IRB 360-3/1130 3 kg 1130 mm"),
             "diameter": dict(varde=1130, enhet="mm",
                              citat=r"IRB 360-3/1130 3 kg 1130 mm"),
         },
         ej_belagda={"rackvidd": "se IRB 360-1/1130: ABB publicerar en DIAMETER.",
                     "repeterbarhet": "familjevarde, inte per variant.",
                     "vikt": "bladet anger ingen vikt per variant."}),
    dict(modell="ABB IRB 360-1/1600", tillverkare="ABB",
         vc_namn=["IRB 360-1/1600"], url=ABB_360,
         uppgifter={
             "nyttolast": dict(varde=1, enhet="kg",
                               citat=r"IRB 360-1/1600 1 kg 1600 mm"),
             "diameter": dict(varde=1600, enhet="mm",
                              citat=r"IRB 360-1/1600 1 kg 1600 mm"),
         },
         ej_belagda={"rackvidd": "se IRB 360-1/1130: ABB publicerar en DIAMETER.",
                     "repeterbarhet": "familjevarde, inte per variant.",
                     "vikt": "bladet anger ingen vikt per variant."}),

    # ---------------- ABB IRB 910SC: grinden faller, och det ar svaret ------
    dict(modell="ABB IRB 910SC-3/0.55", tillverkare="ABB",
         vc_namn=["IRB 910SC-3/0.55"], bank_uri="bank://robot/abb_irb_910sc_3_0550",
         url=ABB_910, uppgifter={},
         ej_belagda={
             "nyttolast": "Tabellrubriken 'Robot version Reach Payload (kg)*' "
                          "bar EN parentesenhet (kg) pa plats 0, medan radens "
                          "tal pa plats 0 ar rackvidden 0.55. Rubriken skriver "
                          "ingen enhet vid Reach, sa kolumngrinden kan inte "
                          "binda 3 till kg. Kallan sager dessutom 'Rated: 3, "
                          "Max: 6' - tva tal, och vilket VC:s MaxPayload 3.0 "
                          "avser ar inte lasbart har.",
             "rackvidd": "Samma tabell: enheten (m) star efter 'Axis max speed' "
                         "i den utdragna texten, inte efter 'Reach'. Lopetexten "
                         "sager 'individual reaches of 450 mm, 550 mm and 650 "
                         "mm, respectively' - en koppling via ordet "
                         "'respectively', vilket ar en positionslasning over en "
                         "mening och inte en tabellkolumn.",
             "repeterbarhet": "bladet anger repeterbarhet PER AXEL (Axis 1 + "
                              "Axis 2 ±0.015 mm, Axis 3 ±0.01 mm), aldrig ett "
                              "samlat TCP-varde.",
             "vikt": "bladet anger ingen vikt.",
             "diameter": "ABB anger rackvidd for 910SC, inte diameter.",
         },
         not_="Enda posten i korpusen dar dokumentet FINNS och grinden anda "
              "sager nej. Det ar avsikten: en kolumnlasning som inte gar att "
              "verifiera far inte bli ett tal."),

    # ---------------- FANUC ----------------
    dict(modell="FANUC LR Mate 200iD/7L", tillverkare="Fanuc",
         vc_namn=["LR Mate 200iD/7L"], bank_uri="bank://robot/fanuc_lrmate_200id_7l",
         url=FANUC_LRM7L,
         uppgifter={
             "nyttolast": dict(varde=7, enhet="kg",
                               citat=r"at wrist: 7 kg"),
             "rackvidd": dict(varde=911, enhet="mm",
                              citat=r"Max\. reach: 911 mm"),
         },
         ej_belagda={
             "repeterbarhet": "bladets varianttabell har lodrata rubriker som "
                              "utdragningen bryter isar; kolumngrinden kan inte "
                              "binda ±0.01 till 'Repeatability (mm)'.",
             "vikt": "samma tabell, samma skal.",
             "diameter": "FANUC anger rackvidd, inte diameter.",
         }),
    dict(modell="FANUC M-10iD/12", tillverkare="Fanuc",
         vc_namn=["M-10iD/12"], bank_uri="bank://robot/fanuc_m10id_12",
         url=FANUC_M10ID12,
         uppgifter={
             "nyttolast": dict(varde=12, enhet="kg", citat=r"at wrist: 12 kg"),
             "rackvidd": dict(varde=1441, enhet="mm",
                              citat=r"Max\. reach: 1441 mm"),
         },
         ej_belagda={
             "repeterbarhet": "se LR Mate 200iD/7L: lodrata tabellrubriker.",
             "vikt": "se LR Mate 200iD/7L.",
             "diameter": "FANUC anger rackvidd, inte diameter.",
         }),
    # Dokumentet finns, talen star dar - men utdragningen flatar samman
    # kolumnerna sa att varken par- eller kolumngrinden kan verifiera dem.
    dict(modell="FANUC M-710iC/50", tillverkare="Fanuc",
         vc_namn=["M-710iC/50"], bank_uri="bank://robot/fanuc_m710ic_50",
         url=FANUC_M710IC50, uppgifter={},
         ej_belagda={
             "nyttolast": "PDF:ens textutdragning flatar samman tva stycken: "
                          "raden lyder ordagrant 'Max. load capacity Fig. "
                          "3.2at(a)wrist: to (e) 50 show kg the robot "
                          "operating'. Talet 50 och enheten kg star inte "
                          "bredvid varandra, och varianttabellens rubriker ar "
                          "lodrata. Ett oga ser 50 kg; grinden kan inte "
                          "verifiera det, och da skrivs det inte.",
             "rackvidd": "Samma dokument: 'Max. reach: 2050 mmspace. When "
                         "installing peripheral devices' - enheten mm har vuxit "
                         "ihop med nasta ord, sa pargrinden faller.",
             "repeterbarhet": "lodrata tabellrubriker, se ovan.",
             "vikt": "lodrata tabellrubriker, se ovan.",
             "diameter": "FANUC anger rackvidd, inte diameter.",
         },
         not_="Provade ocksa fanuc.eu:s datablad for samma modell: HTTP 404."),

    # ---------------- Universal Robots ----------------
    dict(modell="Universal Robots UR10e", tillverkare="Universal Robots",
         vc_namn=["UR10e"], bank_uri="bank://robot/ur10e", url=UR10E,
         uppgifter={
             "nyttolast": dict(varde=12.5, enhet="kg",
                               citat=r"Payload 12\.5 kg \(27\.6 lbs\)"),
             "rackvidd": dict(varde=1300, enhet="mm",
                              citat=r"Reach 1300 mm \(51\.2 in\)"),
             "repeterbarhet": dict(varde=0.05, enhet="mm",
                                   citat=r"Pose repeatability per ISO 9283 ± 0\.05 mm"),
         },
         ej_belagda={
             "vikt": "techsheetet anger 33.3 kg 'Weight including cable' i en "
                     "kolumn som utdragningen blandar med kraftsensorns rader.",
             "diameter": "UR anger rackvidd, inte diameter.",
         }),
    dict(modell="Universal Robots UR5e", tillverkare="Universal Robots",
         vc_namn=["UR5e"], url=UR5E,
         uppgifter={
             "nyttolast": dict(varde=5, enhet="kg", citat=r"Payload 5 kg"),
             "rackvidd": dict(varde=850, enhet="mm", citat=r"Reach 850 mm"),
             "repeterbarhet": dict(varde=0.03, enhet="mm",
                                   citat=r"repeatability per ISO 9283 ± 0\.03 mm"),
         },
         ej_belagda={"vikt": "se UR10e.",
                     "diameter": "UR anger rackvidd, inte diameter."}),
    dict(modell="Universal Robots UR16e", tillverkare="Universal Robots",
         vc_namn=["UR16e"], url=UR16E,
         uppgifter={
             "nyttolast": dict(varde=16, enhet="kg", citat=r"Payload 16 kg"),
             "rackvidd": dict(varde=900, enhet="mm", citat=r"Reach 900 mm"),
             "repeterbarhet": dict(varde=0.05, enhet="mm",
                                   citat=r"repeatability per ISO 9283 ± 0\.05 mm"),
         },
         ej_belagda={"vikt": "se UR10e.",
                     "diameter": "UR anger rackvidd, inte diameter."}),

    # ---------------- Yaskawa ----------------
    # Belagd hos tillverkaren, men INTE i biblioteket: `vc_namn` ar tom for att
    # ingen komponent pa disken heter GP8. Berikningen far alltsa ingen
    # komponent, och det ar ratt svar - inte en granne.
    dict(modell="Yaskawa MOTOMAN GP8", tillverkare="Yaskawa",
         vc_namn=[], bank_uri="bank://robot/yaskawa_gp8", url=YASKAWA_GP,
         uppgifter={
             "nyttolast": dict(varde=8, enhet="kg", citat=r"GP8 8 kg payload"),
             "rackvidd": dict(varde=727, enhet="mm",
                              citat=r"727 mm horizontal reach"),
             "repeterbarhet": dict(varde=0.01, enhet="mm",
                                   citat=r"0\.01 mm repeatability"),
         },
         ej_belagda={"vikt": "bladet anger ingen vikt i den lasta texten.",
                     "diameter": "Yaskawa anger rackvidd, inte diameter."},
         not_="Ingen komponent i det installerade biblioteket heter GP8."),

    # ---------------- KUKA: tillverkaren har tagit bort modellerna ---------
    dict(modell="KUKA KR 10 R1100 sixx", tillverkare="KUKA",
         vc_namn=["KR 10 R1100 sixx C"], bank_uri="bank://robot/kuka_kr10_r1100",
         url="", uppgifter={},
         ej_belagda={
             "nyttolast": "KUKA:s publika dokumentindex har ingen post for "
                          "sixx-generationen. Produktsidan kr-agilus listar "
                          "bara CR/EX/HM-SC/WP och -2-generationen; "
                          "nedladdningscentralens tre DataSheets for modellen "
                          "ar markerade public=false och gar till en "
                          "inloggningsgatad xpert.kuka.com. Att lana 10 kg fran "
                          "'KR 10 R1100 WP' vore en grannmodells tal.",
             "rackvidd": "se nyttolast: modellen finns inte i KUKA:s publika "
                         "dokumentindex.",
             "repeterbarhet": "se nyttolast.",
             "vikt": "se nyttolast.",
             "diameter": "KUKA anger rackvidd, inte diameter.",
         },
         not_="Biblioteket har 'KR 10 R1100 sixx C', som ar den narmaste "
              "komponenten. Den bindningen ar utskriven, inte gissad."),
    dict(modell="KUKA KR 210 R2700 extra", tillverkare="KUKA",
         vc_namn=["KR 210 R2700 extra"], bank_uri="bank://robot/kuka_kr210_r2700",
         url="", uppgifter={},
         ej_belagda={
             "nyttolast": "KUKA:s nedladdningscentral ger totalResults=0 for "
                          "'KR 210 R2700 extra'. Produktsidan kr-quantec listar "
                          "bara -2-generationen, och den har 2701 mm mot "
                          "extra-variantens 2696 mm enligt tredjepartskallor - "
                          "alltsa INTE utbytbara.",
             "rackvidd": "se nyttolast.",
             "repeterbarhet": "se nyttolast.",
             "vikt": "se nyttolast.",
             "diameter": "KUKA anger rackvidd, inte diameter.",
         },
         not_="Aldsta mekaniska nedladdningsvagen "
              "(kuka.com/-/media/kuka-downloads/imported/...) 301:ar numera till "
              "nedladdningscentralens HTML-skal."),
]


def _uppgift(falt, spec, url, doktext, post):
    """En Uppgift ur ett citat som MASTE sta ordagrant i dokumentet."""
    m = re.search(spec["citat"], doktext, re.I)
    if m is None:
        raise SystemExit(
            "CITATET FINNS INTE i %s\n  falt: %s\n  monster: %s\n"
            "Ett citat som inte gar att hitta i kallan ar inget citat."
            % (url, falt, spec["citat"]))
    citat = m.group(0)
    a = max(0, m.start() - UTDRAG)
    b = min(len(doktext), m.end() + UTDRAG)
    kalla = TD.Kalla(url=url, hamtad=post["hamtad"], sha256=post["sha256"],
                     citat=citat, utdrag=doktext[a:b], dokument=post["fil"])
    kol = spec.get("kolumn")
    return TD.Uppgift(falt=falt, varde=spec["varde"], enhet=spec["enhet"],
                      kalla=kalla,
                      kolumn=TD.Kolumn.fran_json(kol) if kol else None)


def main():
    per_tillverkare = {}
    doktexter = {}
    antal_uppgifter = 0
    for rad in KALLOR:
        url = rad["url"]
        uppgifter = {}
        if rad["uppgifter"]:
            if not url:
                raise SystemExit("%s har uppgifter men ingen url" % rad["modell"])
            if url not in doktexter:
                post, kropp = TD.hamta(url)
                doktexter[url] = (post,
                                  TD.normalisera(TD.dokumenttext(kropp, post["fil"])))
                print("hamtat  %-9s %s" % (post["byte"], url))
            post, doktext = doktexter[url]
            for falt, spec in sorted(rad["uppgifter"].items()):
                uppgifter[falt] = _uppgift(falt, spec, url, doktext, post)
                antal_uppgifter += 1
        blad = TD.Modellblad(modell=rad["modell"], tillverkare=rad["tillverkare"],
                             vc_namn=tuple(rad.get("vc_namn") or ()),
                             bank_uri=rad.get("bank_uri", ""),
                             uppgifter=uppgifter,
                             ej_belagda=dict(rad.get("ej_belagda") or {}))
        d = blad.till_json()
        if rad.get("not_"):
            d["not"] = rad["not_"]
        per_tillverkare.setdefault(rad["tillverkare"], []).append(d)

    os.makedirs(TD.KORPUSKATALOG, exist_ok=True)
    for tillverkare, poster in sorted(per_tillverkare.items()):
        fil = os.path.join(TD.KORPUSKATALOG,
                           re.sub(r"[^a-z0-9]+", "_", tillverkare.lower()) + ".json")
        with open(fil, "w", encoding="utf-8") as f:
            json.dump({"tillverkare": tillverkare,
                       "harkomst": "M-107. Varje uppgift bar url, hamtdatum, "
                                   "sha256 och ett ordagrant citat ur kallan. "
                                   "Enheten ar aldrig harledd ur vardet.",
                       "poster": poster}, f, indent=1, sort_keys=True,
                      ensure_ascii=False)
        print("skrev   %-40s %d modeller" % (os.path.basename(fil), len(poster)))

    korpus = TD.Korpus.las()
    fel = TD.verifiera(korpus, kraev_cache=True)
    for f in fel:
        print("FEL " + f)
    print("\n%d modeller, %d belagda uppgifter, %d fel i verifieringen"
          % (len(korpus), antal_uppgifter, len(fel)))
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
