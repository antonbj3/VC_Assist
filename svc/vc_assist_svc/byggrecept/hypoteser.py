# -*- coding: utf-8 -*-
"""Hypoteserna bakom byggrecepten, som DATA.

Varje pastaende om VC bar sin kalla och sin status:

  BELAGT   star ordagrant i en kallfil under docs/referens/. Citatet finns i
           docs/spec/49_komponentmodellen.md under samma id.
  HYPOTES  harledd ur kallorna men inte matt i en korande VC. Rangordnad
           inom sin fraga: rang 1 provas forst.
  MATT     matt av operatoren i VC 4.10 (uppdraget 2026-09-04), inte ur doken.

Recepten i recept.py provar HYPOTES-raderna i rangordning vid korning och
bokfor utfallet per id i svaret ("forsok"). Sa blir en korning en matning
av hela stegen, inte ett enda ja/nej. Testerna i tests/enhet/test_byggrecept.py
haller ihop tre saker: varje id har en kalla, varje id namns i spec 49, och
varje VC_-namn i texten finns i api_index.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

BELAGT = "BELAGT"
HYPOTES = "HYPOTES"
MATT = "MATT"

_PY = "docs/referens/vc_api/api.xml"
_KONST = "docs/referens/vc_api/constants.xml"
_NET = "docs/referens/vc_dotnet/Create3D.Shared.xml"


@dataclass(frozen=True)
class Hypotes:
    id: str          # fragebokstav + lopnummer, t.ex. "B1"
    fraga: str       # A..G ur uppdraget
    rang: int        # 0 = belagt/matt (ingen provordning), 1 = prova forst
    status: str      # BELAGT | HYPOTES | MATT
    text: str
    kalla: str       # filnamn, plus symbolen citatet star under


HYPOTESER: Tuple[Hypotes, ...] = (
    # ---- A. Vad ar en ComponentProcessor -------------------------------
    Hypotes("A0", "A", 0, MATT,
            "Namnet ComponentProcessor forekommer NOLL ganger i alla tio "
            "kallfiler (api.xml, constants.xml, helpers.xml, "
            "vc_python_api.json, sex .NET-xml). Ingen VC_-konstant skapar "
            "en per dokumentationen; namnet ar internt.",
            "grep -c ComponentProcessor docs/referens/vc_api/* docs/referens/vc_dotnet/*"),
    Hypotes("A1", "A", 1, HYPOTES,
            "ComponentProcessor ar karnans basklass for beteenden som "
            "HANTERAR komponenter: vcFlow/vcContainer-familjen (banor, "
            "behallare, skapare, transportprotokoll). Transport-faltets "
            "egenskap Transport pekar pa ett sadant beteende och Connection "
            "ar portindex i det. Foljd: SystemError vid tilldelning av en "
            "vcMotionPath betyder att py-bindningen saknar sattare for "
            "Ref-typer, inte att banan ar fel klass.",
            _NET + ": ISimInterfaceTransportField 'Field for connecting "
            "containers/behaviors'; ISimConnector 'Used to implement material "
            "flow between containers'"),
    Hypotes("A2", "A", 2, HYPOTES,
            "ComponentProcessor ar transportprotokollet: vcTransport, skapat "
            "med VC_TRANSPORT (BehaviorType.TransportProtocol).",
            _NET + ": ITransportProtocol 'A transportation sender and target "
            "behaviour used to customize and standardize transportation "
            "process'; " + _PY + ": vcTransport"),
    # ---- B. Hur binds ett falt -----------------------------------------
    Hypotes("B0", "B", 0, BELAGT,
            "I .NET bar varje falttyp en TYPAD referens: FlowField.Port "
            "(ISimConnector), SignalField.Signal, HierarchyField.Frame/Node/"
            "IsParent, ProcessorField.Path/Sensor/IsParent, "
            "AttachmentField.Frame/Node/IsParent. Python-ytan visar bara "
            "Properties (List of vcProperty), sa bindningen maste ga via "
            "vcProperty.Value. Det finns ingen Ref-variant av vcProperty och "
            "ingen satt-metod pa vcSimInterfaceField.",
            _NET + ": ISimInterfaceFlowField.Port; " + _PY +
            ": vcSimInterfaceField (Index, Name, Properties, Section, Type)"),
    Hypotes("B1", "B", 1, HYPOTES,
            "p.Value = objekt av EXAKT den typ referensen vantar: en "
            "vcConnector till flodesfaltets Port. Matningen med vcMotionPath "
            "gjordes mot Transport-faltet, vars typ ar en annan.",
            _NET + ": ISimInterfaceFlowField.Port 'Gets or sets the instance "
            "of [ISimConnector] that will be connected when the interface "
            "will be connected'"),
    Hypotes("B2", "B", 2, HYPOTES,
            "p.Value = det AGANDE beteendet (vcMotionPath, vcContainer) och "
            "darefter Connection = kontaktens index i beteendet. Galler "
            "Transport-faltet (se A1).",
            _NET + ": ISimInterfaceTransportField; " + _PY +
            ": vcConnector.Index 'position of the connector in its "
            "behavior's list of connectors'"),
    Hypotes("B3", "B", 3, HYPOTES,
            "p.Value = heltal (kontaktens Index).",
            _PY + ": vcConnector.Index"),
    Hypotes("B4", "B", 4, HYPOTES,
            "p.Value = kontaktens eller beteendets Name som bytestrang. "
            "Redan MATT till SystemError pa Transport-faltet; kvar bara for "
            "flodesfaltet.",
            "uppdraget 2026-09-04, matning 5"),
    Hypotes("B5", "B", 5, HYPOTES,
            "Hoppa over granssnittet: koppla kontakterna direkt, "
            "ut.connect(inn) eller ut.Connection = inn. Risk: .NET sager att "
            "malkontakten maste ligga i SAMMA komponent; Python-doken sager "
            "inget sadant.",
            _PY + ": vcConnector.connect, vcConnector.Connection (RW); " +
            _NET + ": ISimConnector.Connect 'Thrown when connector is not "
            "in this component'"),
    Hypotes("B6", "B", 6, HYPOTES,
            "Om B1-B5 faller gar bindningen INTE via Python: falten maste "
            "sattas en gang i GUI:t (eller .NET) och komponenten sparas med "
            "comp.save(uri); recepten laddar och klonar darefter.",
            _PY + ": vcComponent.save, vcApplication.load, vcComponent.clone"),
    # ---- C. Transportor -------------------------------------------------
    Hypotes("C0", "C", 0, BELAGT,
            "vcMotionPath arver vcFlow OCH vcContainer: den tar emot "
            "(CapacityAvailable, Connectors), lagrar (Capacity, Components) "
            "och for komponenter langs Path, en ordnad lista Frame-features. "
            "Ramar ar 'limmet' mellan geometri och simulering.",
            _PY + ": vcMotionPath <parents>vcBehaviour vcFlow vcContainer"
            "</parents> (rad 7894), Path; " + _NET + ": IFrameFeature 'Frames are used "
            "as glue ... to outline conveyor paths'"),
    Hypotes("C1", "C", 1, HYPOTES,
            "En nyskapad VC_ONEWAYPATH bar fardiga kontakter, en med Type "
            "VC_CONNECTOR_INPUT och en med VC_CONNECTOR_OUTPUT. Valj kontakt "
            "pa Type, aldrig pa index.",
            _PY + ": vcFlow.Connectors, vcConnector.Type 'Input, Output or "
            "Input/Output type port'; " + _KONST +
            ": VC_CONNECTOR_INPUT, VC_CONNECTOR_OUTPUT"),
    Hypotes("C2", "C", 2, HYPOTES,
            "Banan far inga kontakter av sig sjalv. Da finns ingen Python-vag "
            "att skapa dem: createConnector finns bara pa "
            "vcComponentFlowProxy, och IFlowBehavior.CreateConnector kastar "
            "nar beteendet inte stoder dynamiska kontakter.",
            _PY + ": vcComponentFlowProxy.createConnector; " + _NET +
            ": IFlowBehavior.SupportsDynamicConnectors"),
    Hypotes("C3", "C", 3, HYPOTES,
            "Minsta transportor: VC_ONEWAYPATH + tva VC_FRAME (start, slut) "
            "+ tva VC_ONETOONEINTERFACE med varsin sektion (Frame satt) och "
            "ett VC_FLOWFIELD bundet till in- respektive utkontakten. Inga "
            "sensorer, ingen styrning.",
            _PY + ": vcNode.createBehaviour, vcFeature.createFeature, "
            "vcSimInterface.createSection, vcSimInterfaceSection.createField"),
    # ---- D. Matare och sanka ---------------------------------------------
    Hypotes("D0", "D", 0, BELAGT,
            "VC_CONTAINER och VC_CONVEYORTRANSPORTCONTROLLER ar inte "
            "beteendetyper: BehaviorType-uppraknningen i .NET saknar dem men "
            "har ComponentContainer, OneWayPath, ComponentCreator, "
            "ContainerFiller, OneToOneInterface. Behallaren heter darfor "
            "VC_COMPONENTCONTAINER.",
            _NET + ": F:VisualComponents.Create3D.BehaviorType.*; "
            "uppdraget matning 6"),
    Hypotes("D1", "D", 1, HYPOTES,
            "Matare: VC_COMPONENTCREATOR (Interval, Limit, TemplateComponent "
            "eller Part) + ett ut-granssnitt bundet till skaparens "
            "utkontakt. Skaparen skjuter sjalv till kopplad utkontakt nar "
            "kapacitet finns.",
            _PY + ": vcComponentCreator.Interval, Limit, TemplateComponent, "
            "BlockingOptimization 'the creator will not check for capacity "
            "rather listen for event'"),
    Hypotes("D2", "D", 1, HYPOTES,
            "Sanka: VC_COMPONENTCONTAINER med stor Capacity och "
            "ContentVisible=False + ett in-granssnitt bundet till "
            "inkontakten. Den LAGRAR; att ta bort komponenter kraver ett "
            "skriptbeteende, och det stoppar bryggans simulering (M-13, "
            "skrivgrind.skapar_skriptbeteende). Sankan ar darfor arligt en "
            "osynlig behallare, inte en fornstorare.",
            _PY + ": vcContainer.Capacity, ContentVisible (W); "
            "ext/vc_addon/vc_assist/skrivgrind.py SKRIPTTYPER"),
    Hypotes("D3", "D", 2, HYPOTES,
            "VC_CONTAINERFILLER (vcFlow) kan vara en alternativ sanka eller "
            "matare; kallorna sager bara 'container filler flow behavior'. "
            "Provas sist, semantiken ar okand.",
            _NET + ": IContainerFiller"),
    Hypotes("D4", "D", 1, HYPOTES,
            "Buffert: en VC_ONEWAYPATH med Accumulate=True och Capacity=N "
            "ar ett buffertmagasin med N platser; ingen egen behallare "
            "behovs.",
            _PY + ": vcMotionPath.Accumulate 'components on the path stop "
            "moving when they encounter a blocked component'; "
            "vcContainer.Capacity"),
    # ---- E. canConnect ---------------------------------------------------
    Hypotes("E0", "E", 0, BELAGT,
            "connect kastar i .NET nar 'it is one to one interface and "
            "already connected or interfaces do not match'. Matchning sker "
            "sektion mot sektion (FindMatchingSections, "
            "ISimInterfaceSection.IsCompatibleWith) och faltens ORDNING "
            "utvarderas.",
            _NET + ": ISimInterface.Connect, FindMatchingSections; " + _PY +
            ": vcSimInterfaceField.Index 'sections may have compatible "
            "fields but cannot connect because the order of fields differ'"),
    Hypotes("E1", "E", 1, HYPOTES,
            "Tva flodesfalt ar kompatibla nar bada har bunden Port och "
            "portarna har MOTSATT Type: Output mot Input. Riktningen bor i "
            "kontaktens Type, inte i faltet. Ut-sidan ar den vars Port ar "
            "VC_CONNECTOR_OUTPUT.",
            _NET + ": AutoPlugFlowDirection.Downstream 'Connect only to the "
            "components defining an material flow output'"),
    Hypotes("E2", "E", 2, HYPOTES,
            "Ett falt utan bunden referens (Port/Transport = None) matchar "
            "aldrig. Det ar darfor canConnect gav False i alla nio matta "
            "uppstallningarna: inget falt var bundet.",
            "uppdraget matning 4 och 7"),
    Hypotes("E3", "E", 3, HYPOTES,
            "Faltens NAMN maste vara lika pa bada sidor. Recepten ger bada "
            "sidor namnet Flow sa att variabeln ar eliminerad.",
            _PY + ": vcSimInterfaceField.Name"),
    Hypotes("E4", "E", 4, HYPOTES,
            "Connection=1 pa Transport-faltet ar portindex i det bundna "
            "beteendet (A1). Alternativ: en riktningsuppraknning.",
            "uppdraget matning 4"),
    Hypotes("E5", "E", 5, HYPOTES,
            "Ett fysiskt granssnitt (IsAbstract=False) vars sektion saknar "
            "Frame matchar inte. Med IsAbstract=True behovs ingen ram.",
            _PY + ": vcSimInterfaceSection.Frame 'If belonging to physical "
            "interface'; " + _NET + ": ISimInterface.IsLogical 'not "
            "connectable by plug and play'"),
    # ---- F. Ramen ----------------------------------------------------------
    Hypotes("F0", "F", 0, BELAGT,
            "Section.Frame ar en vcFeature (RW) och maste vara en "
            "Frame-feature. Den skapas med "
            "node.RootFeature.createFeature(VC_FRAME, namn) och placeras "
            "genom PositionMatrix.",
            _PY + ": vcSimInterfaceSection.Frame, vcFeature.createFeature, "
            "vcFeature.PositionMatrix; " + _NET +
            ": ISimInterfaceSection.Frame 'Thrown when feature is not of "
            "type IFrameFeature'; FeatureType.Frame"),
    Hypotes("F1", "F", 1, HYPOTES,
            "Vid koppling laggs sektionsramarna pa varandra och comp2 "
            "snappas till comp1. Ut-ramen bor da vara vriden 180 grader "
            "kring Z sa att nasta bana fortsatter i samma riktning.",
            _PY + ": vcApplication.connectComponents 'comp2 is snapped to "
            "comp1'"),
    Hypotes("F2", "F", 2, HYPOTES,
            "Ramarna laggs pa varandra utan vridning; ut-ramen ska da "
            "vara ovriden.",
            _PY + ": vcSimInterface.AngleTolerance"),
    # ---- G. Gar det via Python -------------------------------------------
    Hypotes("G0", "G", 0, BELAGT,
            "Varje steg utom bindningen finns namngivet pa Python-ytan: "
            "createComponent, createBehaviour, createFeature(VC_FRAME), "
            "Path, createSection, createField, Properties, IsAbstract, "
            "Frame, canConnect, connect, connectComponents.",
            _PY + ": vcApplication, vcNode, vcFeature, vcSimInterface, "
            "vcSimInterfaceSection, vcMotionPath"),
    Hypotes("G1", "G", 1, HYPOTES,
            "Det GAR via Python om B1 (eller B2) haller. Faller B1-B4 gar "
            "det INTE utan GUI/.NET en gang (B6) eller kontaktkoppling "
            "utanfor granssnitten (B5). Den lokala katalogen ar matt tom, "
            "sa 'ladda en fardig' ar ingen vag.",
            "uppdraget 2026-09-04; " + _PY),
)

PER_ID = {h.id: h for h in HYPOTESER}


def per_fraga(fraga: str) -> Tuple[Hypotes, ...]:
    """Hypoteserna for en fraga i provordning (rang 0 forst = belagt)."""
    return tuple(sorted((h for h in HYPOTESER if h.fraga == fraga),
                        key=lambda h: (h.rang, h.id)))


def provordning(fraga: str) -> Tuple[str, ...]:
    """Bara de id som ska PROVAS, i rangordning."""
    return tuple(h.id for h in per_fraga(fraga) if h.status == HYPOTES)
