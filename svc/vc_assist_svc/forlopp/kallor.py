# -*- coding: utf-8 -*-
"""Källorna: hur ett pågående arbete matar förloppsytan.

Var och en av de här funktionerna är en översättning, och en översättning är
precis det ställe där ett ord kan bytas ut. De är därför avsiktligt korta och
gör en enda sak: de KOPIERAR grindens egna ord, de sammanfattar dem aldrig.
`test_forlopp_kallor.py` jämför tecken för tecken.

Mätt läge före den här filen (M-64): systemet hade **sju rapportytor**, och
**noll** av dem gav en text en människa kan läsa MEDAN körningen pågår. Två
gick att läsa live men lämnade `dict`, och fem fanns över huvud taget inte
förrän det drivande anropet hade returnerat.

Varje funktion nedan tar `Forlopp` först, som en utskrift tar sin ström först.
"""
from __future__ import annotations

from typing import Any, Dict, Sequence

from .handelser import Forloppsfel
from .yta import Forlopp


# ------------------------------------------------------------ stationsgrind

def fran_stationsdom(f: Forlopp, dom, korordning: Sequence[str] = ()) -> None:
    """Grind 1-4 in i förloppet, varje grinds EGNA utdata ordagrant.

    En grind som inte kördes blir en OVISSHET, aldrig ett grindutfall.
    Tystnad är aldrig ett godkännande (I3), och en överhoppad grind som
    räknades som grön vore samma falska grönt som `stationsgrind.py` redan
    vägrar producera.
    """
    if not korordning:
        from ..plc.stationsgrind import KORORDNING
        korordning = KORORDNING
    for namn in korordning:
        if namn not in dom.forgrindar:
            f.vet_inte(namn, "grinden kördes inte och lämnade inget skäl")
            continue
        utfall = dom.forgrindar[namn]
        if utfall is True:
            # En GODKÄND grinds egna ord skrivs INTE ut. Doktrinen i
            # `50_grindar.md` handlar om domen som FÄLLDE: den får inte
            # skrivas om på vägen. `Stationsdom.text()` gör samma val, och
            # skälet är att en användare som drunknar i grönt inte läser det
            # röda.
            f.grind(namn, True)
            continue
        egen = dom.utdata.get(namn) or ""
        if egen.strip():
            # Grinden KÖRDE och skrev något. Dess ord går vidare orörda.
            f.grind(namn, False, egen)
        else:
            # Ingen egen utdata: grinden kunde inte köra. Det är en ovisshet.
            f.vet_inte(namn, str(utfall))


# ------------------------------------------------------------- reparationen

def fran_reparationsprotokoll(f: Forlopp, protokoll) -> None:
    """Reparationsslingans varv, dess ej körda grindar och dess utfall.

    `LOST` är inte guld och blir därför inte ett `SVAR`: `50_grindar.md` säger
    att endast en körning i VC befordrar kandidat till guld. Slingan lämnar
    en KANDIDAT, och det står i klartext i stället för att gömmas bakom ett
    grönt ord.
    """
    from ..plc.reparation import (UTFALL_LAST, UTFALL_LOST, UTFALL_TAK,
                                  UTFALL_TYSTNAD)
    for varv in protokoll.varv:
        namn = "varv %d" % varv.nummer
        if varv.upprepar is not None:
            f.vet_inte(namn, "upprepar varv %d; domen kan inte bli en annan"
                       % varv.upprepar)
            continue
        if varv.ok:
            f.grind(namn, True)
            continue
        for d in varv.fallande:
            f.grind("%s %s" % (namn, d.grind), False, d.utdata)
    for gnamn in sorted(protokoll.ej_korda):
        f.vet_inte(gnamn, protokoll.ej_korda[gnamn])
    if protokoll.utfall == UTFALL_LOST:
        f.vet_inte("ögats dom",
                   "slingan lämnar en kandidat; endast en körning i VC "
                   "befordrar kandidat till guld (50_grindar.md)")
    elif protokoll.utfall == UTFALL_LAST:
        f.fall("slingan är låst: samma kropp igen, och domen kan inte bli "
               "en annan")
    elif protokoll.utfall == UTFALL_TAK:
        f.fall("slingan nådde taket %d varv utan att grindarna höll"
               % protokoll.max_varv)
    elif protokoll.utfall == UTFALL_TYSTNAD:
        f.fall("modellen svarade varken text eller anrop")


# ---------------------------------------------------------------- kopplaren

def fran_kopplarvarv(f: Forlopp, varv) -> None:
    """Ett kopplarvarv. Ett fallet varv fäller INTE körningen.

    Kopplaren tål tre raka fel innan den ger upp (M-39). Ett enstaka fallet
    varv är alltså ett anrop som föll, inte en körning som föll, och
    visningen får inte blanda ihop dem: läget FALLET är absorberande, och att
    sätta det på en hicka vore att låsa en körning som lever.
    """
    namn = "kopplarvarv %d" % varv.nr
    # Ett varv är en HÄNDELSE, inte ett steg i planen. Lades det som ett steg
    # skulle tusen varv göra planen tusen rader lång och räkningen "N av M
    # klara" meningslös.
    if varv.fel:
        f.lagg("VERKTYG_FEL", varv.fel, steg=namn, ordagrant=varv.fel)
    else:
        f.lagg("VERKTYG_KLART",
               "ok" if varv.totalt_ms is None else "%.1f ms" % varv.totalt_ms,
               steg=namn)
    if varv.oga_fel:
        f.vet_inte("inskott varv %d" % varv.nr,
                   "värdena nådde inte ögats tidsaxel: %s" % varv.oga_fel)


def fran_ogonkoppling(f: Forlopp, sammanfattning: Dict[str, Any]) -> None:
    """Vad som INTE kom fram till ögats tidsaxel (M-42).

    Fyra utfall kan inte tigas ihjäl, och tre av dem är ovissheter: ett värde
    som lagrades utan tidsaxel räknas som gammalt, ett inskott till ett stängt
    öga gick ingenstans, och ett avbrott är ett hål i serien med skäl.
    """
    s = sammanfattning or {}
    if s.get("oga_stangt"):
        f.vet_inte("PLC på ögats axel",
                   "%d inskott gick till ett stängt öga och lagrades aldrig"
                   % s["oga_stangt"])
    if s.get("utan_axel"):
        f.vet_inte("PLC-värdenas tid",
                   "%d värden lagrades utan giltig simuleringstid och räknas "
                   "som gamla (M-42)" % s["utan_axel"])
    if s.get("brutna"):
        f.vet_inte("PLC-seriens hål",
                   "%d avbrott: serien har hål med skäl i stället för gamla "
                   "tal" % s["brutna"])
    if s.get("klockbakat"):
        f.vet_inte("simuleringsklockan",
                   "%d stämplar låg i framtiden; klockan har gått bakåt "
                   "(sim.reset)" % s["klockbakat"])


def kor_kopplaren(f: Forlopp, kopplare, varv: int) -> int:
    """Kör kopplaren `varv` varv och för protokoll EFTER VARJE VARV.

    Detta är hela poängen med fasen i en funktion: förloppet går att läsa
    mellan två varv, inte bara när allt är över. Ger kopplaren upp blir det
    ett FALL med kopplarens egna ord, inte ett undantag som försvinner.

    Returnerar antalet körda varv.
    """
    from ..plc.kopplare import Kopplarfel
    kord = 0
    for _ in range(int(varv)):
        try:
            v = kopplare.kor_varv()
        except Kopplarfel as fel:
            # Kopplaren hann lägga sitt sista varv i listan innan den kastade.
            if kopplare.varv:
                fran_kopplarvarv(f, kopplare.varv[-1])
            f.fall(str(fel))
            break
        kord += 1
        fran_kopplarvarv(f, v)
    if kopplare.oga is not None:
        fran_ogonkoppling(f, kopplare.oga.sammanfattning())
    return kord


# --------------------------------------------------------------- guldgrinden

def fran_guldbeslut(f: Forlopp, beslut) -> None:
    """Guldgrindens beslut, ordagrant ur `Beslut.text()`."""
    f.guld(beslut.text())


# ------------------------------------------------------------------- planen

# Planens statusar, ur `plan/korning.py`. De KOPIERAS hit i stället för att
# importeras, av samma skäl som `stationsgrind.py` kopierar grindnamnen:
# förloppsytan är ett presentationslager och ska inte dra in planeringslagrets
# hela importkedja för fem strängar. `test_forlopp_kallor.py` läser
# `korning.py` som text och håller ihop de två listorna.
PLAN_KORD = "kord"
PLAN_HOPPAD = "hoppad"
PLAN_FALLEN = "fallen"
PLAN_KOAD = "koad"
PLAN_EJ_UTFORD = "ej_utford"
PLANSTATUSAR = (PLAN_KORD, PLAN_HOPPAD, PLAN_FALLEN, PLAN_KOAD,
                PLAN_EJ_UTFORD)


def fran_planprotokoll(f: Forlopp, protokoll) -> None:
    """Planens steg och deras utfall in i förloppet.

    Ett koat steg blir `KO_VANTAR`, och det är avsiktligt: en plan som står
    och väntar på operatörens godkännande ARBETAR inte, och en visning som
    säger att den gör det låter operatören vänta på sig själv.

    En okänd status är ett fel, inte en tyst nedgradering: en post som föll
    igenom alla grenar hade blivit osynlig i visningen.
    """
    KORD, HOPPAD = PLAN_KORD, PLAN_HOPPAD
    FALLEN, KOAD, EJ_UTFORD = PLAN_FALLEN, PLAN_KOAD, PLAN_EJ_UTFORD
    for post in protokoll:
        if post.status not in PLANSTATUSAR:
            raise Forloppsfel(
                "okänd planstatus %r för steget %s; en post som inte passar "
                "någon gren blir osynlig i visningen"
                % (post.status, post.steg))
        if post.status == KORD:
            f.steg_klart(post.steg)
        elif post.status == FALLEN:
            f.steg_foll(post.steg, post.skal)
        elif post.status == HOPPAD:
            f.steg_hoppat(post.steg, post.skal)
        elif post.status == KOAD:
            f._steg(post.steg)
            f.ko_vantar(post.qid or post.steg, post.skal)
        elif post.status == EJ_UTFORD:
            f.vet_inte(post.steg, post.skal)
