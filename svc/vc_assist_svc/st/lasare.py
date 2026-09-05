# -*- coding: utf-8 -*-
"""Läsare: ST-text in, modell ut.

Rekursiv nedstigning. Ingen "återhämtning" efter ett syntaxfel: första felet
kastas och validatorn rapporterar det. Skälet är fail-closed (I3) — en läsare
som gissar sig förbi ett fel bygger en modell som inte är programmet, och
sedan dömer alla kontroller ovanför om fel text.

Blocken bokförs på en stack medan de öppnas. Det är därför läsaren kan säga
"END_WHILE på rad 20 avslutar en IF som började på rad 12" i stället för
"oväntat nyckelord", och det är hela skillnaden mellan en användbar och en
oanvändbar balanskontroll.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from . import modell as M
from . import stdbibliotek as SB
from . import typer as T
from .fel import Syntaxfel
from .lexer import AVSLUTARE, Token, tokenisera

# Skydd mot att en djupt nästlad källa fäller läsaren med RecursionError i
# stället för en läsbar anmärkning.
#
# Storheten är NÄSTLINGSNIVÅER i källan — en per `(`, per argumentlista och
# per index — inte parserramar. Skillnaden var mätt (M-99): räknaren ökade en
# gång per prioritetsnivå i NIVAER, så en parentes kostade åtta steg och det
# verkliga taket låg vid ÅTTA parenteser medan meddelandet sa 64. En modell
# som fick tillbaka "djupare än 64 nivåer" på `iA := ((((((((iB))))))));`
# hade ingen väg att laga felet: talet i meddelandet fanns inte i koden.
#
# Taket mäts mot läsarens verkliga kapacitet, inte mot en gissning:
# `test_lasarens_djuptak_ligger_under_uppmatt_kapacitet` bisekerar
# RecursionError med guarden avstängd. MÄTT 2026-09-05 vid
# sys.getrecursionlimit() == 1000: 89 nästlingsnivåer bar, den 90:e föll.
# 64 lämnar 25 nivåers marginal och är samtidigt det tal meddelandet redan
# lovade.
MAX_DJUP = 64  # Satt av M-99: uppmatt kapacitet 89 nivaer, 25 i marginal.
MAX_SATSDJUP = 228  # Satt av M-108: uppmatt kapacitet 326 nivaer, 98 i marginal.

# Operatorer per prioritetsnivå, lägst bindning först. IEC 61131-3, tabell 71.
NIVAER = (
    ("OR",),
    ("XOR",),
    ("AND", "&"),
    ("=", "<>"),
    ("<", ">", "<=", ">="),
    ("+", "-"),
    ("*", "/", "MOD"),
)


class Lasare(object):
    def __init__(self, kalla: str):
        self.tk: List[Token] = tokenisera(kalla)
        self.p = 0
        self.djup = 0
        self.blockstack: List[Tuple[str, int]] = []
        self.blocktypnamn = set(SB.BLOCK) | self._forhandsscanna_block()

    # ---- tokenhantering -------------------------------------------------

    def _forhandsscanna_block(self):
        """Namnen på funktionsblock som deklareras i samma fil.

        Behövs innan deklarationerna läses: `k : Kvitto;` är en blockinstans
        om Kvitto är ett FUNCTION_BLOCK och en struktur annars, och det
        avgör vad `k.Q` betyder.
        """
        ut = set()
        for i, t in enumerate(self.tk[:-1]):
            if t.sort == "NYCKELORD" and t.nyckel == "FUNCTION_BLOCK":
                n = self.tk[i + 1]
                if n.sort == "IDENT":
                    ut.add(n.text.upper())
        return ut

    def _forbi_kommentar(self, j: int) -> int:
        while j < len(self.tk) and self.tk[j].sort == "KOMMENTAR":
            j += 1
        return j

    def _kika(self, n=0) -> Token:
        """Tittar framåt UTAN att flytta positionen.

        Att kika förbi en kommentar fick inte konsumera den: en fristående
        kommentar i satsläge hör till modellen, och en kik som råkade äta upp
        den gjorde att skrivarens utdata inte gick att läsa tillbaka
        oförändrad. Provet som fällde det är
        test_sekvensen_gar_att_lasa_tillbaka_och_skrivs_likadant.
        """
        j = self._forbi_kommentar(self.p)
        for _ in range(n):
            j = self._forbi_kommentar(j + 1)
        return self.tk[j] if j < len(self.tk) else self.tk[-1]

    def _ta(self) -> Token:
        self.p = self._forbi_kommentar(self.p)
        t = self.tk[self.p]
        if t.sort != "SLUT":
            self.p += 1
        return t

    def _ar(self, sort, text=None, n=0) -> bool:
        t = self._kika(n)
        if t.sort != sort:
            return False
        return text is None or t.nyckel == text.upper()

    def _ta_om(self, sort, text=None) -> Optional[Token]:
        if self._ar(sort, text):
            return self._ta()
        return None

    def _krav(self, sort, text=None, vad=None) -> Token:
        if self._ar(sort, text):
            return self._ta()
        t = self._kika()
        vantat = vad or (text if text else sort)
        raise Syntaxfel("SYNTAX", t.rad,
                        "väntade %s men fick %s" % (vantat, self._beskriv(t)))

    @staticmethod
    def _beskriv(t: Token) -> str:
        if t.sort == "SLUT":
            return "filens slut"
        return "%r" % t.text

    # ---- enhet ----------------------------------------------------------

    def las_enhet(self) -> M.Enhet:
        typer, globala, pouer = [], [], []
        while not self._ar("SLUT"):
            t = self._kika()
            if t.sort != "NYCKELORD":
                raise Syntaxfel("SYNTAX", t.rad,
                                "väntade PROGRAM, FUNCTION_BLOCK, FUNCTION, TYPE "
                                "eller VAR_GLOBAL men fick %s" % self._beskriv(t))
            if t.nyckel == "TYPE":
                typer.extend(self._las_typblock())
            elif t.nyckel == "VAR_GLOBAL":
                globala.append(self._las_varblock())
            elif t.nyckel in ("PROGRAM", "FUNCTION_BLOCK", "FUNCTION"):
                pouer.append(self._las_pou())
            else:
                raise Syntaxfel("SYNTAX", t.rad,
                                "%s hör inte hemma på filnivå" % t.text)
        return M.Enhet(tuple(typer), tuple(globala), tuple(pouer))

    def _las_typblock(self) -> List[M.Strukturdef]:
        start = self._krav("NYCKELORD", "TYPE")
        self.blockstack.append(("TYPE", start.rad))
        ut = []
        while not self._ar("NYCKELORD", "END_TYPE"):
            if self._ar("SLUT"):
                raise self._obalans("TYPE", start.rad, "END_TYPE")
            namn = self._krav("IDENT", vad="ett typnamn")
            self._krav("OP", ":")
            sr = self._krav("NYCKELORD", "STRUCT",
                            vad="STRUCT (bara strukturer stöds i TYPE)")
            self.blockstack.append(("STRUCT", sr.rad))
            falt = []
            while not self._ar("NYCKELORD", "END_STRUCT"):
                if self._ar("SLUT"):
                    raise self._obalans("STRUCT", sr.rad, "END_STRUCT")
                dekls = self._las_deklarationsrad()
                for d in dekls:
                    if isinstance(d.typ, T.Pekare):
                        raise Syntaxfel("TYP", d.rad,
                                        "STRUCT-fält av REF_TO-typ stöds inte "
                                        "(backend genererar fel C++: IEC_INT i stället för pekare)")
                falt.extend(dekls)
            self._ta()
            self.blockstack.pop()
            self._krav("OP", ";")
            ut.append(M.Strukturdef(namn.text, tuple(falt), namn.rad))
        self._ta()
        self.blockstack.pop()
        return ut

    def _obalans(self, oppnare, rad, vantad):
        return Syntaxfel("BALANS", rad,
                         "%s på rad %d avslutas aldrig; %s saknas"
                         % (oppnare, rad, vantad))

    # ---- POU ------------------------------------------------------------

    def _las_pou(self) -> M.Pou:
        start = self._ta()
        sort = start.nyckel
        namn = self._krav("IDENT", vad="POU-namn")
        returtyp = None
        if sort == "FUNCTION":
            self._krav("OP", ":", vad="':' och returtyp efter funktionsnamnet")
            returtyp = self._las_typ()
        self.blockstack.append((sort, start.rad))
        block = []
        while self._kika().sort == "NYCKELORD" and self._kika().nyckel in M.VARSORTER:
            block.append(self._las_varblock())
        slut = "END_" + sort
        kropp = self._satser({slut})
        if not self._ar("NYCKELORD", slut):
            raise self._obalans(sort, start.rad, slut)
        self._ta()
        self.blockstack.pop()
        return M.Pou(sort, namn.text, tuple(block), tuple(kropp), returtyp, start.rad)

    def _las_varblock(self) -> M.Varblock:
        start = self._ta()
        kval = []
        while self._kika().sort == "NYCKELORD" and self._kika().nyckel in M.KVALIFICERARE:
            kval.append(self._ta().nyckel)
        dekl = []
        while not self._ar("NYCKELORD", "END_VAR"):
            if self._ar("SLUT"):
                raise self._obalans(start.nyckel, start.rad, "END_VAR")
            try:
                dekl.extend(self._las_deklarationsrad())
            except Syntaxfel as f:
                if f.kod != "SYNTAX":
                    raise
                raise Syntaxfel("SYNTAX", f.rad,
                                "%s (inne i %s-blocket fran rad %d; saknas END_VAR?)"
                                % (f.text, start.nyckel, start.rad))
        slut = self._ta()
        # Bara ett semikolon som star PA SAMMA RAD som END_VAR hor till
        # blocket. Utan den avgransningen at END_VAR-raden upp kroppens
        # forsta tecken: ett program vars hela kropp ar `;` blev plotsligt
        # godkant, och just den kroppen ar T7 i fas7_stationen.md.
        if self._ar("OP", ";") and self._kika().rad == slut.rad:
            self._ta()
        return M.Varblock(start.nyckel, tuple(dekl), tuple(kval), start.rad)

    def _las_deklarationsrad(self) -> List[M.Deklaration]:
        namn = [self._krav("IDENT", vad="ett variabelnamn")]
        while self._ta_om("OP", ","):
            namn.append(self._krav("IDENT", vad="ett variabelnamn"))
        adress = None
        if self._ta_om("NYCKELORD", "AT"):
            if len(namn) > 1:
                raise Syntaxfel("SYNTAX", namn[0].rad,
                                "AT-adress går inte att dela mellan flera namn")
            adress = self._krav("ADRESS", vad="en direktadress som %QX0.0").text
        self._krav("OP", ":", vad="':' och en typ")
        typ = self._las_typ()
        init = None
        if self._ta_om("OP", ":="):
            if self._ar("OP", "["):
                init = self._las_faltinit()
            else:
                init = self._uttryck()
        semi = self._krav("OP", ";")
        skyddad = False
        while self.tk[self.p].sort == "PRAGMA" and self.tk[self.p].rad == semi.rad:
            pragma = self.tk[self.p].varde.upper()
            self.p += 1
            if pragma == "SAKERHET":
                skyddad = True
            else:
                raise Syntaxfel("SYNTAX", semi.rad, "okänt pragma {%s}" % pragma)
        kommentar = None
        if self.tk[self.p].sort == "KOMMENTAR" and self.tk[self.p].rad == semi.rad:
            kommentar = self.tk[self.p].varde
            self.p += 1
        return [M.Deklaration(n.text, typ, init, adress, skyddad, kommentar, n.rad)
                for n in namn]

    def _las_typ(self) -> T.Typ:
        t = self._kika()
        if t.sort == "NYCKELORD" and t.nyckel == "REF_TO":
            self._ta()
            mal = self._las_typ()
            return T.Pekare(mal)
        if t.sort == "NYCKELORD" and t.nyckel == "STRING":
            self._ta()
            langd = None
            if self._ta_om("OP", "["):
                langd = int(self._krav("HELTAL", vad="stränglängd").varde)
                self._krav("OP", "]")
            return T.Strang(langd)
        if t.sort == "NYCKELORD" and t.nyckel == "ARRAY":
            self._ta()
            self._krav("OP", "[")
            granser = [self._las_grans()]
            while self._ta_om("OP", ","):
                granser.append(self._las_grans())
            self._krav("OP", "]")
            self._krav("NYCKELORD", "OF")
            element = self._las_typ()
            # Typlagret vaktar sina egna invarianter med ValueError, och
            # `validera` fangar bara Syntaxfel. MATT (M-99):
            # `ARRAY[10..1] OF INT` kom ut ur validera som en OFANGAD
            # ValueError - grinden KRASCHADE i stallet for att doma, och en
            # grind som kraschar lamnar ingen anmarkning at nagon att laga.
            try:
                return T.Falt(element, tuple(granser))
            except ValueError as fel:
                raise Syntaxfel("SYNTAX", t.rad, str(fel))
        if t.sort == "IDENT":
            self._ta()
            stor = t.nyckel
            if stor in T.ELEMENTARA:
                return T.Elementar(stor)
            if stor in self.blocktypnamn:
                return T.Blocktyp(t.text)
            return T.Strukturtyp(t.text)
        raise Syntaxfel("SYNTAX", t.rad, "väntade en typ men fick %s" % self._beskriv(t))

    def _las_grans(self):
        lo = self._heltal_med_tecken()
        self._krav("OP", "..", vad="'..' i fältgränsen")
        hi = self._heltal_med_tecken()
        return (lo, hi)

    def _heltal_med_tecken(self) -> int:
        neg = bool(self._ta_om("OP", "-"))
        t = self._krav("HELTAL", vad="ett heltal")
        return -int(t.varde) if neg else int(t.varde)

    def _las_faltinit(self) -> M.Faltinit:
        start = self._krav("OP", "[")
        if self._ar("OP", "]"):
            raise Syntaxfel("SYNTAX", start.rad, "en fältinitierare kan inte vara tom")
        element = [self._las_faltinit_element()]
        while self._ta_om("OP", ","):
            element.append(self._las_faltinit_element())
        self._krav("OP", "]")
        return M.Faltinit(element=tuple(element), rad=start.rad)

    def _las_faltinit_element(self) -> M.FaltinitElement:
        if self._ar("OP", "["):
            v = self._las_faltinit()
            return M.FaltinitElement(v, None, getattr(v, "rad", 0))
        if self._ar("HELTAL") and self._kika(1).sort == "OP" and self._kika(1).text == "(":
            antal_token = self._ta()
            antal = int(antal_token.varde)
            if antal <= 0:
                raise Syntaxfel("SYNTAX", antal_token.rad,
                                "upprepningsantalet i fältinitieraren måste vara större än 0")
            self._krav("OP", "(")
            if self._ar("OP", "["):
                varde = self._las_faltinit()
            else:
                varde = self._uttryck()
            self._krav("OP", ")")
            return M.FaltinitElement(varde, antal, antal_token.rad)
        v = self._uttryck()
        return M.FaltinitElement(v, None, getattr(v, "rad", 0))

    # ---- satser ---------------------------------------------------------

    def _ar_etikettstart(self) -> bool:
        """Står vi vid en ny CASE-etikett? `10:` och `5..7, 9:` men inte `x := 10`."""
        j = self._forbi_kommentar(self.p)
        if not (self.tk[j].sort == "HELTAL"
                or (self.tk[j].sort == "OP" and self.tk[j].text == "-")):
            return False
        while j < len(self.tk):
            t = self.tk[j]
            if t.sort == "KOMMENTAR":
                j += 1
                continue
            if t.sort == "HELTAL" or (t.sort == "OP" and t.text in ("-", "..", ",")):
                j += 1
                continue
            return t.sort == "OP" and t.text == ":"
        return False

    def _satser(self, slutord, i_case=False) -> Tuple[M.Sats, ...]:
        ut = []
        while True:
            raa = self.tk[self.p]
            if raa.sort == "KOMMENTAR":
                self.p += 1
                ut.append(M.Kommentar(raa.varde, raa.rad))
                continue
            t = self._kika()
            if t.sort == "SLUT":
                return tuple(ut)
            if t.sort == "NYCKELORD" and t.nyckel in slutord:
                return tuple(ut)
            if i_case and self._ar_etikettstart():
                return tuple(ut)
            ut.append(self._sats())

    def _sats(self) -> M.Sats:
        t = self._kika()
        if t.sort == "NYCKELORD":
            n = t.nyckel
            if n == "IF":
                return self._om()
            if n == "CASE":
                return self._fall()
            if n == "FOR":
                return self._for()
            if n == "WHILE":
                return self._medan()
            if n == "REPEAT":
                return self._upprepa()
            if n == "EXIT":
                self._ta()
                self._krav("OP", ";")
                return M.Avbryt(t.rad)
            if n == "RETURN":
                self._ta()
                self._krav("OP", ";")
                return M.Retur(t.rad)
            if n in AVSLUTARE:
                oppnare = self.blockstack[-1] if self.blockstack else None
                if oppnare and AVSLUTARE[n] != oppnare[0]:
                    raise Syntaxfel(
                        "BALANS", t.rad,
                        "%s på rad %d avslutar ett %s som började på rad %d"
                        % (t.text, t.rad, oppnare[0], oppnare[1]))
                raise Syntaxfel("BALANS", t.rad,
                                "%s står här utan att något %s är öppet"
                                % (t.text, AVSLUTARE[n]))
            raise Syntaxfel("SYNTAX", t.rad,
                            "%s kan inte inleda en sats" % t.text)
        if t.sort != "IDENT":
            raise Syntaxfel("SYNTAX", t.rad,
                            "väntade en sats men fick %s" % self._beskriv(t))
        mal = self._postfix(M.Namn(t.text, t.rad), ta_namn=True)
        if isinstance(mal, M.Anrop):
            self._krav("OP", ";")
            return M.Anropssats(mal, t.rad)
        self._krav("OP", ":=", vad="':=' eller ett anrop")
        vh = self._uttryck()
        self._krav("OP", ";")
        return M.Tilldelning(mal, vh, t.rad)

    def _kroppsslut(self, oppnare, rad, vantad):
        if not self._ar("NYCKELORD", vantad):
            raise self._obalans(oppnare, rad, vantad)
        self._ta()
        self._valfritt_semikolon()

    def _valfritt_semikolon(self):
        """Semikolonet efter END_IF, END_CASE, END_FOR, END_WHILE, END_REPEAT
        och END_VAR är valfritt.

        MÄTT i M-51: STruC++ 0.6.6 kompilerar alla fem blockslut både med och
        utan semikolon, medan vårt lager svarade OLÄSLIG på formen utan. Det är
        en falsk rödgrind på något en modell rimligen skriver, och den är dyr:
        grind 2 och 3 kör FÖRE grind 1 (stationsgrind.granska_station), så en
        falsk röd här betyder att kompilatorn aldrig ens får se koden.

        Regeln som blev kvar: ett semikolon FÅR avsluta ett block, men det får
        aldrig stå ensamt som sats. Ett `;` som avslutar något är en
        avslutare; ett `;` som står för sig självt är ingen sats.
        """
        self._ta_om("OP", ";")

    def _om(self) -> M.Om:
        start = self._ta()
        self.blockstack.append(("IF", start.rad))
        if len(self.blockstack) > MAX_SATSDJUP:
            raise Syntaxfel("SYNTAX", start.rad,
                            "satsnästlingen är djupare än %d nivåer" % MAX_SATSDJUP)
        grenar = []
        villkor = self._uttryck()
        self._krav("NYCKELORD", "THEN")
        stopp = {"ELSIF", "ELSE", "END_IF"}
        grenar.append(M.Gren(villkor, self._satser(stopp), start.rad))
        while self._ar("NYCKELORD", "ELSIF"):
            r = self._ta()
            v = self._uttryck()
            self._krav("NYCKELORD", "THEN")
            grenar.append(M.Gren(v, self._satser(stopp), r.rad))
        annars = None
        if self._ta_om("NYCKELORD", "ELSE"):
            annars = self._satser(stopp)
            if self._ar("NYCKELORD", "ELSE"):
                raise Syntaxfel("BALANS", self._kika().rad,
                                "IF på rad %d har två ELSE" % start.rad)
        self._kroppsslut("IF", start.rad, "END_IF")
        self.blockstack.pop()
        return M.Om(tuple(grenar), annars, start.rad)

    def _fall(self) -> M.Fall:
        start = self._ta()
        self.blockstack.append(("CASE", start.rad))
        if len(self.blockstack) > MAX_SATSDJUP:
            raise Syntaxfel("SYNTAX", start.rad,
                            "satsnästlingen är djupare än %d nivåer" % MAX_SATSDJUP)
        uttryck = self._uttryck()
        self._krav("NYCKELORD", "OF")
        grenar = []
        annars = None
        stopp = {"ELSE", "END_CASE"}
        while not self._ar("NYCKELORD", "ELSE") and not self._ar("NYCKELORD", "END_CASE"):
            if self._ar("SLUT"):
                raise self._obalans("CASE", start.rad, "END_CASE")
            r = self._kika().rad
            etiketter = [self._etikett()]
            while self._ta_om("OP", ","):
                etiketter.append(self._etikett())
            self._krav("OP", ":", vad="':' efter CASE-etiketten")
            grenar.append(M.Fallgren(tuple(etiketter),
                                     self._satser(stopp, i_case=True), r))
        if self._ta_om("NYCKELORD", "ELSE"):
            annars = self._satser(stopp)
        self._kroppsslut("CASE", start.rad, "END_CASE")
        self.blockstack.pop()
        if not grenar:
            raise Syntaxfel("SYNTAX", start.rad, "CASE utan en enda gren")
        return M.Fall(uttryck, tuple(grenar), annars, start.rad)

    def _etikett(self) -> M.Etikett:
        lo = self._heltal_med_tecken()
        if self._ta_om("OP", ".."):
            return M.Etikett(lo, self._heltal_med_tecken())
        return M.Etikett(lo)

    def _for(self) -> M.ForSats:
        start = self._ta()
        self.blockstack.append(("FOR", start.rad))
        if len(self.blockstack) > MAX_SATSDJUP:
            raise Syntaxfel("SYNTAX", start.rad,
                            "satsnästlingen är djupare än %d nivåer" % MAX_SATSDJUP)
        var = self._krav("IDENT", vad="styrvariabel")
        self._krav("OP", ":=")
        fran = self._uttryck()
        self._krav("NYCKELORD", "TO")
        till = self._uttryck()
        steg = self._uttryck() if self._ta_om("NYCKELORD", "BY") else None
        self._krav("NYCKELORD", "DO")
        kropp = self._satser({"END_FOR"})
        self._kroppsslut("FOR", start.rad, "END_FOR")
        self.blockstack.pop()
        return M.ForSats(var.text, fran, till, steg, kropp, start.rad)

    def _medan(self) -> M.Medan:
        start = self._ta()
        self.blockstack.append(("WHILE", start.rad))
        if len(self.blockstack) > MAX_SATSDJUP:
            raise Syntaxfel("SYNTAX", start.rad,
                            "satsnästlingen är djupare än %d nivåer" % MAX_SATSDJUP)
        villkor = self._uttryck()
        self._krav("NYCKELORD", "DO")
        kropp = self._satser({"END_WHILE"})
        self._kroppsslut("WHILE", start.rad, "END_WHILE")
        self.blockstack.pop()
        return M.Medan(villkor, kropp, start.rad)

    def _upprepa(self) -> M.Upprepa:
        start = self._ta()
        self.blockstack.append(("REPEAT", start.rad))
        if len(self.blockstack) > MAX_SATSDJUP:
            raise Syntaxfel("SYNTAX", start.rad,
                            "satsnästlingen är djupare än %d nivåer" % MAX_SATSDJUP)
        kropp = self._satser({"UNTIL", "END_REPEAT"})
        if not self._ar("NYCKELORD", "UNTIL"):
            raise self._obalans("REPEAT", start.rad, "UNTIL")
        self._ta()
        villkor = self._uttryck()
        self._kroppsslut("REPEAT", start.rad, "END_REPEAT")
        self.blockstack.pop()
        return M.Upprepa(kropp, villkor, start.rad)

    # ---- uttryck --------------------------------------------------------

    def _uttryck(self, niva=0) -> M.Uttryck:
        # Bara niva 0 är en NY nästlingsnivå. Anropen med niva+1 vandrar
        # nedför prioritetstabellen inom samma nivå och är inte nästling.
        rakna = niva == 0
        if rakna:
            self.djup += 1
            if self.djup > MAX_DJUP:
                raise Syntaxfel("SYNTAX", self._kika().rad,
                                "uttrycket är djupare än %d nivåer" % MAX_DJUP)
        try:
            if niva >= len(NIVAER):
                return self._unar()
            v = self._uttryck(niva + 1)
            while True:
                t = self._kika()
                op = t.nyckel if t.sort in ("OP", "NYCKELORD") else None
                if op == "&":
                    op = "AND"
                if op is None or op not in NIVAER[niva]:
                    return v
                if t.sort == "NYCKELORD" and t.nyckel not in ("AND", "OR", "XOR", "MOD"):
                    return v
                self._ta()
                h = self._uttryck(niva + 1)
                v = M.Binar(op, v, h, t.rad)
        finally:
            if rakna:
                self.djup -= 1

    def _unar(self) -> M.Uttryck:
        t = self._kika()
        if t.sort == "NYCKELORD" and t.nyckel == "NOT":
            self._ta()
            return M.Unar("NOT", self._unar(), t.rad)
        if t.sort == "OP" and t.text == "-":
            self._ta()
            return M.Unar("-", self._unar(), t.rad)
        if t.sort == "OP" and t.text == "+":
            self._ta()
            return self._unar()
        return self._potens()

    def _potens(self) -> M.Uttryck:
        """`a ** b`, IEC 61131-3:s exponentoperator.

        Den ligger utanför NIVAER av två skäl. Den binder HÅRDARE än unärt
        minus — `-a ** b` är `-(a ** b)` — och den är högerassociativ, medan
        alla nivåer i NIVAER är vänsterassociativa. Att lägga den i tabellen
        hade alltså krävt två undantag i tabellens egen tolkning.

        MÄTT i M-51: STruC++ 0.6.6 kompilerar `**`; vårt lager svarade
        OLÄSLIG.
        """
        v = self._primar()
        if self._ar("OP", "**"):
            t = self._ta()
            return M.Binar("**", v, self._unar(), t.rad)
        return v

    def _primar(self) -> M.Uttryck:
        t = self._ta()
        if t.sort == "OP" and t.text == "(":
            v = self._uttryck()
            self._krav("OP", ")")
            return v
        if t.sort == "HELTAL":
            return M.Literal("HELTAL", t.text, t.varde, self._typprefix(t.text), t.rad)
        if t.sort == "REAL":
            return M.Literal("REAL", t.text, t.varde, self._typprefix(t.text), t.rad)
        if t.sort == "TID":
            # varde = millisekunder, None om formen är ogiltig. Skälet hämtar
            # validatorn ur lexer.tolka_tidliteral, som är enda stället där
            # formregeln står skriven.
            return M.Literal("TID", t.text, t.varde[1], None, t.rad)
        if t.sort == "STRANG":
            return M.Literal("STRANG", t.text, t.varde, None, t.rad)
        if t.sort == "NYCKELORD" and t.nyckel in ("TRUE", "FALSE"):
            return M.Literal("BOOL", t.nyckel, t.nyckel == "TRUE", None, t.rad)
        if t.sort == "NYCKELORD" and t.nyckel == "NULL":
            return M.Literal("NULL", t.nyckel, None, None, t.rad)
        if t.sort == "IDENT":
            return self._postfix(M.Namn(t.text, t.rad), ta_namn=False)
        raise Syntaxfel("SYNTAX", t.rad,
                        "väntade ett värde men fick %s" % self._beskriv(t))

    @staticmethod
    def _typprefix(text: str) -> Optional[str]:
        if "#" in text:
            fore = text.split("#", 1)[0].upper()
            if fore in T.ELEMENTARA:
                return fore
        return None

    def _postfix(self, bas: M.Uttryck, ta_namn: bool) -> M.Uttryck:
        if ta_namn:
            self._ta()
        while True:
            if self._ar("OP", "^"):
                t = self._ta()
                bas = M.Avreferering(bas, t.rad)
                continue
            if self._ar("OP", "."):
                self._ta()
                falt = self._krav("IDENT", vad="ett fältnamn")
                bas = M.Medlem(bas, falt.text, falt.rad)
                continue
            if self._ar("OP", "["):
                r = self._ta()
                index = [self._uttryck()]
                while self._ta_om("OP", ","):
                    index.append(self._uttryck())
                self._krav("OP", "]")
                bas = M.Element(bas, tuple(index), r.rad)
                continue
            if self._ar("OP", "(") and isinstance(bas, M.Namn):
                self._ta()
                argument = []
                if not self._ar("OP", ")"):
                    argument.append(self._argument())
                    while self._ta_om("OP", ","):
                        argument.append(self._argument())
                self._krav("OP", ")")
                bas = M.Anrop(bas.ident, tuple(argument), bas.rad)
                continue
            return bas

    def _argument(self) -> M.Argument:
        if self._ar("IDENT") and (self._ar("OP", ":=", 1) or self._ar("OP", "=>", 1)):
            namn = self._ta()
            pil = self._ta()
            return M.Argument(self._uttryck(), namn.text, pil.text == "=>", namn.rad)
        t = self._kika()
        return M.Argument(self._uttryck(), None, False, t.rad)


def las(kalla: str) -> M.Enhet:
    return Lasare(kalla).las_enhet()
