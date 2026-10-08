# 413 Broome Street, the small pink store

The pink corner store at Broome and Lafayette, Manhattan, on the ground floor of the Sing Tao Daily building (413 Broome / 188 Lafayette). About 20 ft of Lafayette and 23.5 ft of Broome; Ceremonia's flagship since 2023. Public data, gathered 8 October 2026.

**Live page:** https://feldtdesign-ship-it.github.io/broome-413/

- `index.html` – one page. Part one: scroll-driven camera through the block model, the building, the store, next door, the trains, the block, the landmark rules, open items. Part two: the numbers.
- `og.jpg` – the link-preview card, 1200 × 630.
- `data/` – the pulls. `data/raw/` is the building's own record: PLUTO, storefront registry, ACRIS, DOB, ECB, Landmarks permits and violations, 311, crashes, curbs.
- `frames/` – Blender renders of the block and the building, and DOT camera frames from 8 October 2026.
- `assets/lafayette_188.glb` – the Draco-compressed block model with the Sing Tao building and the pink store in detail.
- `build/` – in the order they run:
  1. `pull_raw.py` – the building's record
  2. `pull.py` – transit, cameras, map layers, weather
  3. `build_188.py` – the Blender block model and the building (`lafayette_188.blend`), run headless
  4. `cameras_188.py` – street-level cameras and renders
  5. `make_template_188.py` – assembles `laf_template.html` from the Mott page and `laf_body.html`
  6. `build_page_188.py` – data into `index.html`
  7. `make_card.sh` – `og.jpg`

## What is drawn, not measured

The building outline and roof height are the city's. The pink store's windows, doors, bathroom and cash wrap are drawn from street photographs and a visit, not measured. It measures about 450 sq ft from the street against 750 sq ft published. The rest of the ground floor is drawn from photographs and Parasol's published plan for the room next door.

## Where the numbers come from

- MTA subway hourly ridership, data.ny.gov, complexes 409 (Spring St), 623 (Canal St), 17 (Prince St), 619 (Broadway-Lafayette)
- MTA bus stop-level hourly ridership, stops inside 300 m (M1, M55)
- NYC DOT Automated Traffic Volume Counts: nothing at this corner; Spring St eastbound at Cleveland Place, 2015
- DOF Storefront Registry, BBL 1004730040 and every filing within 250 m
- NYC Motor Vehicle Collisions, Planimetric Database, building footprints, street centerline, 2015 street tree census, PLUTO, ACRIS, DOB, ECB, LPC permits and violations, 311
- Parasol Projects' listing for 188 Lafayette; Retail Dive and Beauty Independent on the Ceremonia shop, 2023

Nobody counts the people passing this corner. The page says so where it matters.
