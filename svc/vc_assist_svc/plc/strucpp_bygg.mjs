// STruC++-omslag: kompilera ST och skriv ALLA fyra artefakter.
//
// Varför det här finns i stället för `strucpp <fil> -o <fil>`:
// **MÄTT 2026-09-04.** CLI:t i strucpp 0.6.6 skriver bara generated.cpp och
// generated.hpp. Det skriver aldrig generated_debug.cpp eller debug-map.json,
// och båda behövs:
//
//   * OpenPLC v4.2.1:s runtime-shim (core/strucpp_runtime/runtime_v4_entry.cpp)
//     refererar strucpp::debug::debug_array_count. Utan generated_debug.cpp
//     bygger .so:n men vägrar laddas:
//       "undefined symbol: _ZN7strucpp5debug17debug_array_countE"
//   * OPC UA-plugin adresserar PLC-minnet med heltalsparet (arr, elem), och
//     paret finns bara i debug-map.json. Det går inte att härleda ur %IX0.0
//     eller ur variabelnamnet.
//
// Kompilatorns egna API (`compile()` i dist/index.js) returnerar båda. Det är
// samma kompilator, samma anrop som editorn gör — omslaget uppfinner ingenting,
// det skriver bara ut det CLI:t kastar bort.
//
// Anrop:  node strucpp_bygg.mjs <strucpp-paketkatalog> <in.st> <utkatalog> <md5>
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [paketKatalog, inFil, utKatalog, md5] = process.argv.slice(2);
if (!paketKatalog || !inFil || !utKatalog) {
    console.error("anrop: node strucpp_bygg.mjs <paketkatalog> <in.st> <utkatalog> [md5]");
    process.exit(2);
}

const api = await import(pathToFileURL(path.join(paketKatalog, "dist", "index.js")).href);
const nodapi = await import(pathToFileURL(path.join(paketKatalog, "dist", "node", "index.js")).href);

const libsKatalog = path.join(paketKatalog, "libs");
const bibliotek = fs.existsSync(libsKatalog) ? nodapi.discoverStlibs(libsKatalog) : [];

const kalla = fs.readFileSync(inFil, "utf8");
const res = api.compile(kalla, { debug: true, md5: md5 || "0", libraries: bibliotek });

if (!res.success) {
    // Grind 1 fäller här. Felen går ut som JSON på stderr så att anroparen kan
    // visa rad och kolumn i stället för en textklump.
    console.error(JSON.stringify({ fel: res.errors }, null, 2));
    process.exit(1);
}

fs.mkdirSync(utKatalog, { recursive: true });
fs.writeFileSync(path.join(utKatalog, "generated.cpp"), res.cppCode);
fs.writeFileSync(path.join(utKatalog, "generated.hpp"), res.headerCode);
if (!res.debugTableCpp || !res.debugMap) {
    // Fail-closed: utan debugtabellen laddas .so:n inte, och utan kartan går
    // OPC UA-noderna inte att binda. Halva artefakter är värre än inga.
    console.error(JSON.stringify({ fel: "kompilatorn gav ingen debugtabell eller debugkarta" }));
    process.exit(3);
}
fs.writeFileSync(path.join(utKatalog, "generated_debug.cpp"), res.debugTableCpp);
fs.writeFileSync(path.join(utKatalog, "debug-map.json"), JSON.stringify(res.debugMap, null, 2));

console.log(JSON.stringify({
    varningar: res.warnings.map((w) => ({ rad: w.line, text: w.message })),
    lov: res.debugMap.leaves.length,
}));
