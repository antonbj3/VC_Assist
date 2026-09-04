# -*- coding: utf-8 -*-
"""Felklasser for verktygslagret.

S9 i 96_ingen_skuld.md: inga tysta undantag. Varje avslag har en egen klass
och ett meddelande som namner VAD som var fel, sa att orkestreraren kan mata
tillbaka det till modellen utan att gissa.
"""
from __future__ import annotations


class Verktygsfel(Exception):
    """Bas for allt som gar fel i verktygslagret."""


class OkantVerktyg(Verktygsfel):
    """Modellen anropade ett namn som inte finns i registret (I9)."""


class Argumentfel(Verktygsfel):
    """Argumenten haller inte verktygets schema.

    Bar HELA problemlistan, inte bara det forsta felet: modellen ska kunna
    ratta allt i ett svar i stallet for att provas fram ett fel i taget.
    """

    def __init__(self, verktyg, problem):
        self.verktyg = verktyg
        self.problem = list(problem)
        Exception.__init__(
            self, "%s: %d fel i argumenten: %s"
            % (verktyg, len(self.problem), "; ".join(self.problem)))


class Avstangt(Verktygsfel):
    """Verktyget ar avslaget av formagegrinden (36_versioner.md).

    Kastas INNAN nagon kod genereras eller skickas. Skalet namner ytan som
    saknas, sa felet aldrig kommer som ett AttributeError langt senare.
    """

    def __init__(self, verktyg, skal):
        self.verktyg = verktyg
        self.skal = skal
        Exception.__init__(self, "%s ar avstangt: %s" % (verktyg, skal))


class Svarsfel(Verktygsfel):
    """Bryggan svarade, men svaret haller inte verktygets returns-schema.

    I3 fail-closed: ett svar som inte gar att lita pa ar inte ett svar.
    """


class Schemafel(Verktygsfel):
    """Sjalva verktygsdefinitionen ar felaktig. Fyrar vid import, inte i drift."""
