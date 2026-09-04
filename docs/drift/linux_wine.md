# Drift: Linux med Wine

Gäller **endast** när VC körs under Wine. Inget här är systemkrav på Windows.

| Krav | Värde | Varför |
|---|---|---|
| Wine | **≥ 11.15**, här 11.16 i `/opt/wine-devel` | under det saknar bcrypt `HashBlockLength`; licensmotorn dör med 677005 |
| d3d9 | **DXVK** (native) | wined3d nekar `CheckDeviceFormat(X8R8G8B8, RENDERTARGET\|DYNAMIC, SURFACE)` och ger delad yta med handle 0 |
| d3dx9_43, d3dcompiler_43 | **native** | Wines egna är ofullständiga; ger svart 3D-vy och evig omritningsloop |
| CPU | `taskset -c 0-11` på 13600K | håller rendertråden på P-kärnor |
| Nice | **ingen nedprioritering** | GUI ska vara snabbt |

Startskript: `~/bin/vc.sh`.

Licens bakom skolans VPN: `~/bin/vpn-skolan.sh start`. Split tunnel,
bara skolans nät, ingen DNS-påverkan.
