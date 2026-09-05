# Härkomst — PLCopen TC6 XML-schemat

`tc6_xml_v201.xsd` är **inte vår fil**. Den ligger här för att grinden i
`svc/vc_assist_svc/plc/plcopen.py` ska ha en domare som inte är vår egen kod
(`docs/spec/85_bankkontraktet.md` §2: ett facit får aldrig komma ur koden som
döms), och för att provet ska gå att köra utan nät.

| Fält | Värde |
|---|---|
| Fil | `tc6_xml_v201.xsd` |
| Hämtad från | `https://raw.githubusercontent.com/beremiz/beremiz/master/plcopen/tc6_xml_v201.xsd` |
| Hämtad | 2026-09-05 |
| Storlek | 85 975 byte |
| `sha256` | `591b92ba65018a77c32ab9e606abf27bd810cb1f7761d972a85689531c51e20f` |
| `targetNamespace` | `http://www.plcopen.org/xml/tc6_0201` |

Beremiz är en riktig, använd IEC 61131-3-IDE med öppen källkod som läser och
skriver just det här formatet — dess egen projektfil `plc.xml` **är** ett
TC6 v2.01-dokument. OpenPLC Editor är en bekräftad fork av Beremiz och bär
samma XSD-filer.

## Vilken version det INTE är

PLCopen skriver själva att IEC 61131-10:2019 — den standardiserade
efterföljaren — **inte** är bakåtkompatibel:

> *"This work was done within the IEC committee based on the work of PLCopen
> TC6 – XML and resulted in IEC 61131-10 PLC open XML exchange format. This new
> version is not compatible to previous versions of PLCopen XML."*
> — PLCopen, `plcopen_iec61131-10_announcement.pdf`, hämtad från plcopen.org
> 2026-09-05.

Vår export skriver alltså **TC6 v2.01**, inte IEC 61131-10. Det är ett medvetet
val: v2.01 är versionen CODESYS, TwinCAT och Beremiz dokumenterar stöd för, och
den enda vars schema är fritt tillgängligt. Se `docs/matningar/M-154_plcopen_export_ut.md` och `M-155_vad_som_oppnas_hos_tillverkaren.md`.
