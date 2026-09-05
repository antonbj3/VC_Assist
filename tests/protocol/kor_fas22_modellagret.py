# -*- coding: utf-8 -*-
"""Fas 22: modellagret som grind.

`docs/spec/23_llm_granssnitt.md`, `24_samtalsloopen.md` och
`25_kontextbudget.md` ar 1 292 rader spec om hur en sprakmodell ska tala med
systemet. Ingen av dem hade en fas. Den har korningen gor dem till TAL, och
till ett rott utfall nar nagot av lagrets tre tysta fel intraffar.

VAD KORNINGEN SVARAR PA
-----------------------
  1. Far verktygsschemat plats under sitt eget tak? (Nej. Talet star nedan.)
  2. Hur ofta kapas ett verktygssvar, och VAD kapas - matt over repots egna
     190 riktiga verktygssvar, inte over pahittade.
  3. Vilket tak BINDER forst, per fonsterstorlek?
  4. Traffar urvalet det turen verkligen behovde? Matt over 95 riktiga turer
     ur efterlevnadsbanken, med turens egna anrop som facit.
  5. Gar varje riktig tur en vag som star i tillstandsmaskinen, och hur stor
     del av maskinen besoks?

DE TRASIGA FALLEN AR FASENS POANG
---------------------------------
Ett lager som bara mater ser alltid gront ut. Var och en av fixturerna nedan
MASTE falla, med sin egen kod:

    ett kapat svar som SER HELT UT              K2_SER_HELT_UT
    ett svar klippt pa tecken                   K1_OGILTIG_JSON
    ett internt konsistent men kort svar        K2 mot ravaran
    ett for stort svar som tappar felet         K4_FEL_TAPPAT
    tystnad som markts som klar                 T3_TYST_GODKANNANDE
    en trimning utan handelse                   B1_TYST_TRIMNING
    en handelse utan trimning                   B2_HANDELSE_UTAN_TRIMNING
    en budget som inte rymmer det skyddade      Budgetfel
    en omskriven domsrad                        O4/O1
    en bortklippt HONESTY-sektion               O3_SKYDDAD_SEKTION
    ett bortkapat minsta MINDIST-avstand        O2_FYND_BORTA
    en ordlista som fyrar pa fel storhet        den naiva domaren MOT var
    ett namn turen behover, sammanfattat bort   S1_NAMN_BORTA
    avkortad svald i en sammanfattning          S2_AVKORTAD_SVALD

    python3 tests/protocol/kor_fas22_modellagret.py [--json ut.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Kontextbudgeten haller sig sjalv fore anropet, varje trimning bar en "
        "TRIMMAD-handelse, ett kapat verktygssvar sager alltid att det kapades "
        "och behaller den del som bar felet, och varje riktig tur gar en vag "
        "som star i turens tillstandsmaskin.",
    "under_prov": (
        "svc/vc_assist_svc/llm/budget.py",
        "svc/vc_assist_svc/llm/kapning.py",
        "svc/vc_assist_svc/llm/ogontrim.py",
        "svc/vc_assist_svc/llm/scenvy.py",
        "svc/vc_assist_svc/llm/tur.py",
        "svc/vc_assist_svc/llm/urval.py",
    ),
    "facit":
        "repots egna verktygssvar och turer: 190 svar ur DATA_HANDLERS, nio "
        "ogonrapporter ur banken, 95 turer ur efterlevnadsbanken - med turens "
        "EGNA anrop som facit for urvalstraffen",
    "facitkalla":
        "data som fanns fore lagret: verktygsregistret, bank/uppgifter/, "
        "bank/katalog_index.json och harness/fallor.py",
    "facitkalla_filer": (
        "svc/vc_assist_svc/harness/fallor.py",
        "bank/katalog_index.json",
    ),
    "trasiga_fall": (
        "ett kapat svar som ser helt ut maste fallas",
        "tystnad fran modellen far aldrig bli ett godkant slutsvar",
        "ett verktygssvar som spranger budgeten far inte tappa den del som "
        "bar felet",
        "en ordlista som fyrar pa fel storhet: OK i ett parnamn och OK i ett "
        "signalnamn pa en rad vars dom ar MISSING",
    ),
    "kraver": ("inget",),
    "matningar": ("M-102",),
}

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "tests", "protocol", "stod")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fas22_fixturer as FX                                        # noqa: E402
from vc_assist_svc import verktyg as V                             # noqa: E402
from vc_assist_svc.harness import fallor as F                      # noqa: E402
from vc_assist_svc.harness import kanal as Kn                      # noqa: E402
from vc_assist_svc.harness import loop as L                        # noqa: E402
from vc_assist_svc.harness import modell as Mo                     # noqa: E402
from vc_assist_svc.harness.fel import Modellfel                    # noqa: E402
from vc_assist_svc.harness.instruktioner import las_korpus         # noqa: E402
from vc_assist_svc.harness.sammansattning import bygg_systemprompt  # noqa: E402
from vc_assist_svc.llm import budget as B                          # noqa: E402
from vc_assist_svc.llm import delar as D                           # noqa: E402
from vc_assist_svc.llm import kapning as K                         # noqa: E402
from vc_assist_svc.llm import matt, ogontrim as O, profil, scenvy  # noqa: E402
from vc_assist_svc.llm import tur, urval as U                      # noqa: E402
from vc_assist_svc.llm.fel import Budgetfel                        # noqa: E402

# Fonsterstorlekar att mata mot. 8 000 och 32 000 ar sma fonster, 128 000 ar
# 23_llm_granssnitt.md:s eget rakneexempel, 200 000 ett stort.
FONSTER = (8000, 32000, 128000, 200000)


# ==========================================================================
# 1. Verktygsschemat mot sitt eget tak
# ==========================================================================

def schemat():
    hela = U.schematext(V.REGISTER, sorted(V.REGISTER))
    alltid = U.alltid_med(V.REGISTER)
    alltid_text = U.schematext(V.REGISTER, alltid)
    write = sum(1 for v in V.REGISTER.values() if v.effect == "write")
    return {
        "verktyg": len(V.REGISTER),
        "write": write,
        "byte": len(hela.encode("utf-8")),
        "medel_byte": len(hela.encode("utf-8")) // len(V.REGISTER),
        "tokens": matt.tokens(hela),
        "minsta_fonster": matt.tokens(hela) * 10,
        "alltid_med": len(alltid),
        "alltid_byte": len(alltid_text.encode("utf-8")),
        "alltid_tokens": matt.tokens(alltid_text),
        "alltid_minsta_fonster": matt.tokens(alltid_text) * 10,
    }


# ==========================================================================
# 2. Riktiga verktygssvar mot budgeten
# ==========================================================================

def svaren(par):
    storlekar = sorted(s.byte() for s, _c in par)
    sjalv = 0
    for s, c in par:
        listor = [n for n in K.listfalt(c)
                  if isinstance((s.resultat or {}).get(n), list)]
        if (isinstance(s.resultat, dict) and len(listor) == 1
                and (K.FALT_VISADE in s.resultat or K.FALT_ANTAL in s.resultat)):
            sjalv += 1
    ut = {"antal": len(par), "minsta": storlekar[0], "median":
          storlekar[len(storlekar) // 2], "storsta": storlekar[-1],
          "sjalvkontrollerbara": sjalv, "per_fonster": {}}
    for fonster in FONSTER:
        prof = profil.provprofil(kontext_tokens=fonster,
                                 svar_tokens_max=int(fonster * 0.10))
        tak = B.Budget(prof).tak_byte(B.P_RESULTAT)
        kapade = 0
        hanvisningar = 0
        anmarkta = []
        for s, c in par:
            if s.byte() <= tak:
                continue
            kapad, notis = K.kapa(s, tak, c)
            kapade += 1
            if notis.hanvisning:
                hanvisningar += 1
            fel = K.granska(kapad, c) + K.granska_par(s, kapad, c)
            if fel:
                anmarkta.append((s.verktyg, [a.kod for a in fel]))
        ut["per_fonster"][fonster] = {
            "tak_byte": tak, "kapade": kapade, "hanvisningar": hanvisningar,
            "anmarkta": anmarkta,
        }
    return ut


# ==========================================================================
# 3-5. Turerna: budgeten, urvalstraffen och tillstandsmaskinen
# ==========================================================================

def turerna(fonster=32000):
    prompt = bygg_systemprompt(las_korpus())
    prof = profil.provprofil(kontext_tokens=fonster,
                             svar_tokens_max=int(fonster * 0.12))
    budget = B.Budget(prof)
    tackning = tur.Tackning()

    olagliga = []
    utan_slut = []
    traffade = 0
    behovda = 0
    missade_lasande = []
    missade_skrivande = []
    urvalsstorlekar = []
    trim_per_post = {}
    delade = 0
    bokforingsfel = []
    stoppkoder = {}

    for f in F.ALLA:
        p = L.Harness(modell=Mo.AttrappModell(f.svar),
                      kanal=Kn.Attrappkanal(f.manus or {})).kor(
            f.uppgift, ogonrapport=f.ogonrapport, guldbeslut=f.guld)
        fel = tur.granska(p)
        if fel:
            olagliga.append((f.id, fel))
        else:
            tackning.lagg(tur.spar_ur_protokoll(p))
        kod = tur.stoppkod(p)
        stoppkoder[kod] = stoppkoder.get(kod, 0) + 1

        # urvalstraffen: turens EGNA anrop ar facit
        vill = [a.namn for s in f.svar for a in s.anrop]
        valda = U.valj(V.REGISTER, f.uppgift)
        urvalsstorlekar.append(len(valda))
        t, n = U.traff(vill, valda)
        traffade += t
        behovda += n
        for namn in vill:
            if namn in valda:
                continue
            v = V.REGISTER.get(namn)
            if v is None:
                continue          # anropet hade inget namn - en trasig fixtur
            (missade_skrivande if v.effect == "write"
             else missade_lasande).append(namn)

        # budgeten over turen
        namn = sorted(valda)
        delar = [D.systempromptdel(prompt.text), D.uppgiftsdel(f.uppgift)]
        if f.med_signalkarta:
            delar.append(D.signalkartedel(str(F.SIGNALKARTA)))
        delar.append(D.schemadel(
            V.REGISTER, namn, U.schematext(V.REGISTER, namn),
            lambda mal, u=f.uppgift: U.valj(V.REGISTER, u, tak=20)))
        if f.ogonrapport:
            delar.append(D.ogondel(f.ogonrapport))
        for i, utfall in enumerate(p.utfallen):
            svar = K.Verktygssvar(
                verktyg=utfall.verktyg, argument=dict(utfall.argument),
                ok=utfall.ok, resultat=utfall.resultat,
                fel=utfall.fel,
                felnyckel=("%s/FEL" % utfall.verktyg) if not utfall.ok else "")
            delar.append(D.resultatdel(
                svar, V.REGISTER[utfall.verktyg].returns, nr=i))
        try:
            plan = budget.planera(delar)
        except Budgetfel as e:
            bokforingsfel.append((f.id, "Budgetfel: %s" % e))
            continue
        for post, antal in plan.trimmade_per_post().items():
            trim_per_post[post] = trim_per_post.get(post, 0) + antal
        if plan.delad:
            delade += 1
        fel = B.granska(delar, plan)
        if fel:
            bokforingsfel.append((f.id, fel))

    for namn, p in FX.egna_turer():
        fel = tur.granska(p)
        if fel:
            olagliga.append((namn, fel))
        else:
            tackning.lagg(tur.spar_ur_protokoll(p))

    return {
        "turer": len(F.ALLA),
        "egna_turer": len(FX.egna_turer()),
        "olagliga_spar": olagliga,
        "utan_slutlage": utan_slut,
        "urvalstraff": (traffade, behovda),
        "missade_lasande": missade_lasande,
        "missade_skrivande": missade_skrivande,
        "urval_medel": sum(urvalsstorlekar) // len(urvalsstorlekar),
        "trim_per_post": trim_per_post,
        "delade_turer": delade,
        "bokforingsfel": bokforingsfel,
        "stoppkoder": stoppkoder,
        "tackning_lagen": (len(tackning.lagen), len(tur.TILLSTAND)),
        "tackning_overgangar": (len(tackning.overgangar), len(tur.OVERGANGAR)),
        "obesokta_lagen": tackning.obesokta_lagen(),
        "obesokta_overgangar": tackning.obesokta_overgangar(),
        "natbara": tackning.natbara(),
        "obyggda": len(tur.OBYGGDA),
        "ej_nabara": len(tur.EJ_NABARA),
        "tackningsrad": tackning.rad(),
    }


# ==========================================================================
# 6. Ogontrimningen over riktiga rapporter
# ==========================================================================

def ogat():
    rapporter = FX.ogonrapporter()
    ut = {"riktiga": len(rapporter), "storsta": max(len(r.encode("utf-8"))
                                                    for r in rapporter),
          "trimmade": 0, "anmarkta": []}
    for r in rapporter:
        trimmad, notiser = O.trimma(r, 10000)
        if notiser:
            ut["trimmade"] += 1
        fel = O.granska(r, trimmad)
        if fel:
            ut["anmarkta"].append(fel)
    lang = FX.lang_rapport()
    trimmad, notiser = O.trimma(lang, 1200)
    ut["lang_fore"] = len(lang.encode("utf-8"))
    ut["lang_efter"] = len(trimmad.encode("utf-8"))
    ut["lang_notiser"] = [n.rad() for n in notiser]
    ut["lang_anmarkta"] = O.granska(lang, trimmad)
    # ordlistan pa fel storhet
    riggad = FX.rapport_med_ok_i_namn()
    naiva = [r.strip() for r in riggad.splitlines()
             if r.startswith("  ") and FX.naiv_ok(r)]
    var_trimmad, _n = O.trimma(riggad, 400)
    ut["naiv_skulle_trimma"] = len(naiva)
    ut["var_domare_behaller_fynden"] = (
        "STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s"
        in var_trimmad
        and "MINDIST kritiska_paret 12.000mm t=9.000s" in var_trimmad)
    return ut


# ==========================================================================
# 7. DE TRASIGA FALLEN
# ==========================================================================

def _sjalvkontrollerbart(par):
    for svar, schema in par:
        listor = [n for n in K.listfalt(schema)
                  if isinstance((svar.resultat or {}).get(n), list)]
        if (len(listor) == 1 and isinstance(svar.resultat, dict)
                and K.FALT_ANTAL in svar.resultat
                and len(svar.resultat[listor[0]]) > 4):
            return svar, schema
    raise SystemExit("inget sjalvkontrollerbart svar i korpusen")


def trasiga(par):
    """[(namn, vantad kod, fick, ok, vad fallet bevisar)]"""
    ut = []
    svar, schema = _sjalvkontrollerbart(par)

    def lagg(namn, vantad, koder, varfor):
        ut.append((namn, vantad, list(koder), vantad in koder, varfor))

    lagg("kapat svar som ser helt ut", K.K2_SER_HELT_UT,
         [a.kod for a in K.granska(FX.ser_helt_ut(svar, schema), schema)],
         "halva listan borta, svarets egen rakning kvar")
    lagg("klippt pa tecken", K.K1_OGILTIG_JSON,
         [a.kod for a in K.granska(FX.parsar_inte(svar), schema)],
         "lasbart for ett oga, oparsbart for allt annat")
    kort = FX.helt_men_kort(svar, schema)
    lagg("internt konsistent men kort", K.K2_SER_HELT_UT,
         [a.kod for a in K.granska_par(svar, kort, schema)],
         "bara en jamforelse med ravaran fanger den")

    fallet = K.Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                            ok=False, resultat=svar.resultat,
                            fel="E_EXEC: VC nekade anropet",
                            felnyckel="%s/E_EXEC" % svar.verktyg)
    utan_fel = K.Verktygssvar(verktyg=svar.verktyg,
                              argument=dict(svar.argument), ok=False,
                              resultat={"components": []},
                              felnyckel="%s/ANNAT" % svar.verktyg)
    lagg("for stort svar som tappade felet", K.K4_FEL_TAPPAT,
         [a.kod for a in K.granska_par(fallet, utan_fel, schema)],
         "det ar precis den delen som behovs")

    # turen
    p = L.Harness(modell=Mo.AttrappModell([]),
                  kanal=Kn.Attrappkanal({})).kor("uppgift")
    p.klar = True
    lagg("tystnad markt som klar", tur.T3_TYST_GODKANNANDE,
         [k.split(":")[0] for k in tur.granska(p)],
         "tystnad ar aldrig ett godkannande (I3)")

    # budgeten
    prof = profil.provprofil(kontext_tokens=400000)
    delar = [D.systempromptdel("B1\nB2\n"), D.uppgiftsdel("u"),
             D.signalkartedel("S BOOL in\n")] + D.huvudboksdelar(
        ["rad %d" % i for i in range(9)])
    plan = B.Budget(prof).planera(delar)
    riggad = B.Plan(profil=prof, delar=list(plan.delar),
                    handelser=list(plan.handelser))
    riggad.delar[-1] = B.Del(post=B.P_HUVUDBOK, id=riggad.delar[-1].id,
                             text="nagot annat")
    lagg("tyst trimning", B.B1_TYST_TRIMNING,
         [k.split(":")[0] for k in B.granska(delar, riggad)],
         "innehallet andrades utan en TRIMMAD-handelse")

    riggad2 = B.Plan(profil=prof, delar=list(plan.delar),
                     handelser=list(plan.handelser) + [
                         B.Trimmad(steg=1, post=B.P_HUVUDBOK,
                                   del_id="huvudbok:0", fore_tokens=5,
                                   efter_tokens=0, vad="pahittad")])
    lagg("handelse utan trimning", B.B2_HANDELSE_UTAN_TRIMNING,
         [k.split(":")[0] for k in B.granska(delar, riggad2)],
         "bokforing utan verklighet")

    liten = profil.provprofil(kontext_tokens=140, svar_tokens_max=19)
    skyddade = [D.systempromptdel("B1 uppdrag\nB2 harda regler\nB5 driftlage\n"),
                D.uppgiftsdel("Koppla roboten till transportoren."),
                D.signalkartedel("ST010_PEC_PART BOOL in\n" * 13)]
    try:
        B.Budget(liten).planera(skyddade)
        koder = []
    except Budgetfel:
        koder = ["Budgetfel"]
    lagg("budget under det skyddade", "Budgetfel", koder,
         "ett fel, aldrig en tyst trimning (S1)")

    # ogat
    lang = FX.lang_rapport()
    lagg("omskriven domsrad", O.O4_OMSKRIVEN_RAD,
         [k.split(":")[0] for k in O.granska(
             lang, lang.replace("EYES VERDICT PASS allt inom marginal",
                                "EYES VERDICT PASS allt sag bra ut"))],
         "en sammanfattning far aldrig bli ett andra omdome")
    lagg("bortklippt HONESTY", O.O3_SKYDDAD_SEKTION,
         [k.split(":")[0] for k in O.granska(
             lang, "\n".join(r for r in lang.splitlines()
                             if "TELEPORT_TRANSFER" not in r) + "\n")],
         "dess franvaro gar inte att skilja fran att den aldrig kordes")
    riggad_mindist = FX.rapport_med_ok_i_namn(antal_mindist=12)
    lagg("minsta MINDIST bortkapad", O.O2_FYND_BORTA,
         [k.split(":")[0] for k in O.granska(
             riggad_mindist,
             "\n".join(r for r in riggad_mindist.splitlines()
                       if "MINDIST kritiska_paret" not in r) + "\n")],
         "raden bar just den storhet sektionen finns for")

    # scenvyn
    poster = [{"name": "KOMP%03d" % i, "uri": None, "category": "transport"}
              for i in range(200)]
    poster[0]["name"] = "ST010"
    scen = K.Verktygssvar(verktyg="list_components", argument={},
                          resultat={"components": poster, "antal": 200,
                                    "avkortad": True})
    vy = scenvy.sammanfatta(scen, ["ST010"], [])
    lagg("namn som turen behover, bortsammanfattat", scenvy.S1_NAMN_BORTA,
         [a.kod for a in scenvy.granska(scen, vy, ["ST010", "KOMP177"])],
         "en miss andrar regel 1; den ar ingen ratt att skruva pa")
    svald = K.Verktygssvar(verktyg=vy.verktyg, argument={},
                           resultat=dict(vy.resultat, avkortad=False),
                           id=vy.id, ur_kalla=vy.ur_kalla, sammanfattning=True)
    lagg("avkortad svald", scenvy.S2_AVKORTAD_SVALD,
         [a.kod for a in scenvy.granska(scen, svald, ["ST010"])],
         "att svalja avkortad ar att gora fail-closed till fail-open")
    return ut


def kontrollen(par):
    """Den GRONA riktningen. En grind som faller pa allt mater ingenting."""
    fel = []
    for svar, schema in par:
        a = K.granska(svar, schema)
        if a:
            fel.append((svar.verktyg, [x.kod for x in a]))
    for r in FX.ogonrapporter():
        f = O.granska(r, r)
        if f:
            fel.append(("ogonrapport", f))
    return fel


# ==========================================================================
# Korningen
# ==========================================================================

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--json")
    a = a.parse_args()

    print("=== FAS 22: MODELLAGRET ===\n")

    s = schemat()
    print("1. Verktygsschemat mot postens tak (10 % av fonstret)")
    print("   verktyg %d (%d skrivande), schema %d byte, medel %d byte"
          % (s["verktyg"], s["write"], s["byte"], s["medel_byte"]))
    print("   hela schemat %d tokens => kraver ett fonster pa %d tokens"
          % (s["tokens"], s["minsta_fonster"]))
    print("   alltid-med-listan %d verktyg, %d tokens => kraver %d tokens"
          % (s["alltid_med"], s["alltid_tokens"],
             s["alltid_minsta_fonster"]))
    print("   => urvalet ar inte valfritt langre. Specen skrev '21 verktyg, "
          "2 %' vid 11 074 byte.\n")

    par = FX.korpus()
    sv = svaren(par)
    print("2. %d RIKTIGA verktygssvar ur repots egna handlare" % sv["antal"])
    print("   byte: minsta %d, median %d, storsta %d"
          % (sv["minsta"], sv["median"], sv["storsta"]))
    print("   svar som bar SIN EGEN rakning: %d av %d"
          % (sv["sjalvkontrollerbara"], sv["antal"]))
    for fonster in FONSTER:
        d = sv["per_fonster"][fonster]
        print("   fonster %6d: postens tak %6d byte, kapade %3d av %d, "
              "hanvisningar %d, anmarkta %d"
              % (fonster, d["tak_byte"], d["kapade"], sv["antal"],
                 d["hanvisningar"], len(d["anmarkta"])))
    print()

    t = turerna()
    print("3. %d riktiga turer ur efterlevnadsbanken" % t["turer"])
    traffade, behovda = t["urvalstraff"]
    print("   urvalstraff %d av %d anrop (%.1f %%), urvalets medelstorlek %d "
          "av %d verktyg"
          % (traffade, behovda, 100.0 * traffade / max(1, behovda),
             t["urval_medel"], len(V.REGISTER)))
    print("   missade anrop: %d lasande, %d skrivande - ett skrivande verktyg"
          % (len(t["missade_lasande"]), len(t["missade_skrivande"])))
    print("   gar inte att gissa ur en svensk fritext; det kommer ur planen")
    print("   turer som maste delas: %d" % t["delade_turer"])
    print("   trimningar per post: %s"
          % (", ".join("%s %d" % kv for kv in sorted(t["trim_per_post"].items()))
             or "inga"))
    print("   stoppkoder: %s"
          % ", ".join("%s %d" % kv for kv in sorted(t["stoppkoder"].items())))
    print("   olagliga spar: %d, bokforingsfel: %d"
          % (len(t["olagliga_spar"]), len(t["bokforingsfel"])))
    print("   plus %d egna turer for de vagar banken aldrig gar"
          % t["egna_turer"])
    print("   %s" % t["tackningsrad"])
    print("   obesokta utan skrivet skal: %d overgangar, lagen: %s"
          % (len(t["obesokta_overgangar"]),
             ", ".join(t["obesokta_lagen"]) or "inga"))
    print()

    o = ogat()
    print("4. Ogontrimningen")
    print("   %d riktiga ogonrapporter, storsta %d byte, trimmade under ett "
          "tak pa 10 000 byte: %d" % (o["riktiga"], o["storsta"],
                                      o["trimmade"]))
    print("   en lang rapport: %d -> %d byte, %d notiser"
          % (o["lang_fore"], o["lang_efter"], len(o["lang_notiser"])))
    for n in o["lang_notiser"]:
        print("     %s" % n)
    print("   ordlistan pa fel storhet: den naiva domaren skulle trimma %d "
          "rader; var domare behaller fynden: %s"
          % (o["naiv_skulle_trimma"],
             "JA" if o["var_domare_behaller_fynden"] else "NEJ"))
    print()

    print("5. Kontrollen (ska INTE falla)")
    gron = kontrollen(par)
    print("   %s: %d anmarkningar pa riktiga svar och rapporter"
          % ("GRON" if not gron else "ROD", len(gron)))
    for x in gron[:5]:
        print("     %s" % (x,))
    print()

    print("6. De trasiga fallen (var och en MASTE falla)\n")
    fall = trasiga(par)
    for namn, vantad, koder, ok, varfor in fall:
        print("   %-3s %-38s %-26s %s"
              % ("ok" if ok else "ROD", namn, vantad,
                 varfor if ok else ("fick %s" % (", ".join(koder) or "inget"))))

    fallda = sum(1 for _n, _v, _k, ok, _w in fall if ok)
    gront = (not gron and fallda == len(fall)
             and not t["missade_lasande"]
             and not t["obesokta_overgangar"]
             and not t["olagliga_spar"] and not t["bokforingsfel"]
             and not o["anmarkta"] and not o["lang_anmarkta"]
             and o["var_domare_behaller_fynden"]
             and all(not d["anmarkta"] for d in sv["per_fonster"].values()))

    print("\n=== UTFALL ===")
    print("  riktiga verktygssvar:      %d" % sv["antal"])
    print("  riktiga turer:             %d" % t["turer"])
    print("  kontrollen:                %s" % ("gron" if not gron else "ROD"))
    print("  trasiga fall fallda:       %d av %d" % (fallda, len(fall)))
    print("  missade LASANDE anrop:     %d (kravet ar 0)"
          % len(t["missade_lasande"]))
    print("  FAS 22: %s" % ("GRON" if gront else "ROD"))

    print("\n  Vad korningen INTE visar:")
    print("    Ingen sprakmodell ar anropad. Turerna kommer ur en attrapp med")
    print("    manus, och tokentalen ar en OMRAKNING ur byte - ingen")
    print("    leverantors tokenisering har rakat var text.")
    print("    Ingen brygga och ingen VC har svarat. De kodgenererande")
    print("    verktygens svar kommer ur deras deklarerade returns.")
    print("    %d av %d riktiga svar bar sin egen rakning; for de ovriga gar"
          % (sv["sjalvkontrollerbara"], sv["antal"]))
    print("    en kapning bara att upptacka genom jamforelse med ravaran.")
    print("    %d av maskinens %d overgangar ar OBYGGDA (kolagret finns i"
          % (t["obyggda"], len(tur.OVERGANGAR)))
    print("    specen men inte i loop.py) och %d ar strukturellt onabara."
          % t["ej_nabara"])
    print("    Ingen tur har alltsa passerat kon - lage KO ar oprovat.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"schema": s, "svar": sv, "turer": t, "ogat": o,
                       "kontroll": gron,
                       "trasiga": [{"namn": n, "vantad": v, "fick": k,
                                    "ok": ok} for n, v, k, ok, _w in fall],
                       "gront": gront}, f, indent=2, ensure_ascii=False,
                      default=str)
        print("\n  skrivet: %s" % a.json)
    return 0 if gront else 1


if __name__ == "__main__":
    sys.exit(main())
