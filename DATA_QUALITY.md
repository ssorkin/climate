# Data Quality Report

Generated 2026-08-27 by `clim check`. Problems in the source data are surfaced here and in `known_issues/`, never silently patched. Anomalies block the nightly deploy.

## Known issues (documented registry)

### Downtown LA (Civic Center) record excluded

*siting, ghcnd 1877, 1999* — id `civic-center-excluded`

The downtown Los Angeles record (GHCN USW00093134) is the most-quoted "Los Angeles" temperature series, but per NWS Technical Memorandum TM-261 it was produced from eight different locations between 1877 and 1999, with instruments 4 to 220+ feet above the ground, mostly on rooftops. It is not a consistent record of one place.

**Handling:** Not charted. Listed in stations/la.yaml under `excluded` with the source, and explained on the site's Methods page. Nearby ground-level stations with stable siting (Pasadena, Long Beach, Burbank, UCLA, Culver City) tell the downtown story.

### Cooperative-observer stations read the thermometer once a day

*measurement, ghcnd * — id `coop-observation-time`

Volunteer (COOP, ids USC*) stations record the 24-hour max/min at a fixed local time, typically 0800 or 1600, and the value is logged on the date of the reading. A high recorded at 0800 mostly happened the previous afternoon. Airport (USW*) stations use calendar days (2400). Some stations changed their observation time during their record, which shifts a small time-of-observation bias.

**Handling:** Values are never shifted or adjusted. Monthly and annual aggregates are robust to the one-day offset. The daily explorer shows the observation time for each period and notes the offset when the reading is before noon. Changes in observation time are surfaced by `clim check` and on each station page.

## Check findings

### completeness

- 🟡 **2025** Fullerton Airport: 2025 has 327/365 TMAX and 327/365 TMIN days
- 🟡 **2021** San Bernardino Airport: 2021 has 321/365 TMAX and 321/365 TMIN days
- 🟡 **2022** San Bernardino Airport: 2022 has 323/365 TMAX and 323/365 TMIN days
- 🟡 **2024** San Bernardino Airport: 2024 has 319/366 TMAX and 319/366 TMIN days
- 🟡 **2025** San Bernardino Airport: 2025 has 325/365 TMAX and 325/365 TMIN days
- 🟡 **2021** Victorville: 2021 has 66/365 TMAX and 66/365 TMIN days
- 🟡 **2023** Victorville: 2023 has 238/365 TMAX and 238/365 TMIN days
- 🟡 **2024** Victorville: 2024 has 327/366 TMAX and 327/366 TMIN days
- 🟡 **2023** Corona Airport: 2023 has 325/365 TMAX and 325/365 TMIN days
- 🟡 **2023** Point Mugu: 2023 has 326/365 TMAX and 326/365 TMIN days
- 🟡 **2024** Downtown LA (USC): 2024 has 139/366 TMAX and 139/366 TMIN days
### freshness

- 🟡 Santa Monica Pier: last TMAX 240 days ago
- 🟡 Ontario Airport: last TMAX 240 days ago
- 🟡 Fullerton Airport: last TMAX 240 days ago
- 🟡 Hawthorne Airport: last TMAX 240 days ago
- 🟡 Riverside Airport: last TMAX 240 days ago
- 🟡 Chino Airport: last TMAX 245 days ago
- 🟡 March Air Reserve Base: last TMAX 240 days ago
- 🟡 San Bernardino Airport: last TMAX 240 days ago
- 🟡 Long Beach Airport: last TMAX 240 days ago
- 🟡 Van Nuys Airport: last TMAX 240 days ago
- 🟡 Camarillo Airport: last TMAX 240 days ago
- 🟡 Burbank Airport: last TMAX 240 days ago
- 🟡 LAX: last TMAX 240 days ago
- 🟡 Palmdale Airport: last TMAX 240 days ago
- 🟡 Los Alamitos: last TMAX 240 days ago
- 🟡 Corona Airport: last TMAX 240 days ago
- 🟡 Oxnard Airport: last TMAX 240 days ago
- 🟡 Point Mugu: last TMAX 240 days ago
- 🟡 John Wayne Airport: last TMAX 240 days ago
- 🟡 Santa Monica Airport: last TMAX 240 days ago
- 🟡 1353 national station(s): last TMAX 240 days ago …
  - 9076070 - S.W. Pier Mi: last TMAX 240 days ago
  - Adak Island: last TMAX 240 days ago
  - Anaktuvuk Auto: last TMAX 240 days ago
  - Anchorage: last TMAX 240 days ago
  - Anchorage Elmendorf AFB: last TMAX 240 days ago
  - Anchorage Lake Hood Sea Plane Ba: last TMAX 240 days ago
### suspect_step

- 🟡 15 national station(s): mean daily highs jumped +4.2 °C between 1985–1989 and 2015–2 …
  - Barter Is WSO Airport: mean daily highs jumped +4.2 °C between 1985–1989 and 2015–2019 — likely a sensor or site change under one station id
  - Bethel Airport: mean daily lows jumped +3.0 °C between 2010–2014 and 2015–2019 — likely a sensor or site change under one station id
  - Bettles Airport: mean daily highs jumped +3.2 °C between 1970–1974 and 1975–1979 — likely a sensor or site change under one station id
  - Kotzebue Airport: mean daily highs jumped -3.2 °C between 2015–2019 and 2020–2024 — likely a sensor or site change under one station id
  - Nenana Municipal Airport: 2012: mean daily highs +6.7 °C off this station's trend line — that year is excluded; likely a sensor or site change under one station id
  - Fresno Chandler Dwtn Airport: 2019: mean daily lows +3.9 °C off this station's trend line — that year is excluded; likely a sensor or site change under one station id
### suspicious_values

- 🟡 Ontario Airport: 2 suspicious unflagged value(s)
  - wide_range on 1969-11-27: tmax=267 tmin=-139
  - wide_range on 1970-06-24: tmax=356 tmin=-178
- 🟡 Long Beach Airport: 1 suspicious unflagged value(s)
  - wide_range on 1949-11-01: tmax=333 tmin=-167
- 🟡 Van Nuys Airport: 1 suspicious unflagged value(s)
  - wide_range on 1974-08-25: tmax=350 tmin=-160
- 🟡 Victorville: 1 suspicious unflagged value(s)
  - 7 identical TMAX values from 2016-02-09
- 🟡 Camarillo Airport: 2 suspicious unflagged value(s)
  - 7 identical TMAX values from 1953-08-21
  - 7 identical TMAX values from 2023-06-24
- 🟡 Burbank Airport: 6 suspicious unflagged value(s)
  - wide_range on 1975-09-07: tmax=311 tmin=-205
  - jump on 2000-10-07: tmax=220 tmin=160
  - wide_range on 2015-06-10: tmax=244 tmin=-233
  - wide_range on 2015-10-24: tmax=350 tmin=-172
  - wide_range on 2015-10-25: tmax=300 tmin=-172
  - wide_range on 2015-10-26: tmax=306 tmin=-172
- 🟡 LAX: 3 suspicious unflagged value(s)
  - 7 identical TMAX values from 1958-06-05
  - 7 identical TMAX values from 1973-07-13
  - 7 identical TMAX values from 2025-07-20
- 🟡 Palmdale Airport: 1 suspicious unflagged value(s)
  - 8 identical TMAX values from 1999-08-21
- 🟡 Los Alamitos: 2 suspicious unflagged value(s)
  - extreme on 2011-03-17: tmax=210 tmin=-370
  - wide_range on 2011-03-17: tmax=210 tmin=-370
- 🟡 Oxnard Airport: 6 suspicious unflagged value(s)
  - 7 identical TMAX values from 1953-08-21
  - 7 identical TMAX values from 1998-07-03
  - 10 identical TMAX values from 2000-07-06
  - 7 identical TMAX values from 2002-04-27
  - 8 identical TMAX values from 2004-10-18
  - 8 identical TMAX values from 2005-04-24
- 🟡 Point Mugu: 4 suspicious unflagged value(s)
  - wide_range on 2018-09-01: tmax=256 tmin=-172
  - wide_range on 2018-09-02: tmax=244 tmin=-172
  - jump on 2018-09-03: tmax=-172 tmin=-172
  - jump on 2018-09-04: tmax=222 tmin=-172
- 🟡 Downtown LA (USC): 1 suspicious unflagged value(s)
  - wide_range on 2012-07-04: tmax=222 tmin=-230
- 🟡 John Wayne Airport: 1 suspicious unflagged value(s)
  - wide_range on 2016-08-15: tmax=322 tmin=-200
- 🟡 Santa Monica Airport: 3 suspicious unflagged value(s)
  - 11 identical TMAX values from 2001-06-03
  - 8 identical TMAX values from 2002-10-21
  - 7 identical TMAX values from 2004-07-28
- 🟡 1441 national station(s): 2 suspicious unflagged value(s) …
  - 9076070 - S.W. Pier Mi: 2 suspicious unflagged value(s)
  - Adak Airport: 3 suspicious unflagged value(s)
  - Ambler Airport: 719 suspicious unflagged value(s)
  - Anaktuvuk Auto: 1412 suspicious unflagged value(s)
  - Anchorage Elmendorf AFB: 101 suspicious unflagged value(s)
  - Anchorage Lake Hood Sea Plane Ba: 2 suspicious unflagged value(s)
### whole_degree_f

- 🟡 Santa Monica Pier: only 25.59% of TMAX values round-trip to whole °F
- 🟡 Ontario Airport: only 83.27% of TMAX values round-trip to whole °F
- 🟡 Fullerton Airport: only 78.10% of TMAX values round-trip to whole °F
- 🟡 Hawthorne Airport: only 76.53% of TMAX values round-trip to whole °F
- 🟡 Riverside Airport: only 77.79% of TMAX values round-trip to whole °F
- 🟡 Chino Airport: only 78.10% of TMAX values round-trip to whole °F
- 🟡 March Air Reserve Base: only 71.38% of TMAX values round-trip to whole °F
- 🟡 San Bernardino Airport: only 38.76% of TMAX values round-trip to whole °F
- 🟡 Long Beach Airport: only 90.28% of TMAX values round-trip to whole °F
- 🟡 Van Nuys Airport: only 75.79% of TMAX values round-trip to whole °F
- 🟡 Victorville: only 73.16% of TMAX values round-trip to whole °F
- 🟡 Camarillo Airport: only 77.70% of TMAX values round-trip to whole °F
- 🟡 Burbank Airport: only 87.20% of TMAX values round-trip to whole °F
- 🟡 LAX: only 97.17% of TMAX values round-trip to whole °F
- 🟡 Palmdale Airport: only 84.60% of TMAX values round-trip to whole °F
- 🟡 Los Alamitos: only 24.80% of TMAX values round-trip to whole °F
- 🟡 Corona Airport: only 69.76% of TMAX values round-trip to whole °F
- 🟡 Oxnard Airport: only 47.93% of TMAX values round-trip to whole °F
- 🟡 Point Mugu: only 95.88% of TMAX values round-trip to whole °F
- 🟡 Downtown LA (USC): only 91.83% of TMAX values round-trip to whole °F
- 🟡 John Wayne Airport: only 69.94% of TMAX values round-trip to whole °F
- 🟡 Santa Monica Airport: only 81.70% of TMAX values round-trip to whole °F
- 🟡 1931 national station(s): only 26.02% of TMAX values round-trip to whole °F …
  - 9076070 - S.W. Pier Mi: only 26.02% of TMAX values round-trip to whole °F
  - Adak Airport: only 38.12% of TMAX values round-trip to whole °F
  - Adak Island: only 25.79% of TMAX values round-trip to whole °F
  - Ambler Airport: only 39.20% of TMAX values round-trip to whole °F
  - Anaktuvuk Auto: only 37.40% of TMAX values round-trip to whole °F
  - Anchorage: only 26.32% of TMAX values round-trip to whole °F
### completeness

- ℹ️ Santa Monica Pier: 14 complete years of 17 (2009-2025); incomplete: 2009, 2016, 2019
- ℹ️ Ontario Airport: 59 complete years of 61 (1943-2025); incomplete: 1945, 2001
- ℹ️ Fullerton Airport: 26 complete years of 29 (1986-2025); incomplete: 1986, 1998, 2025
- ℹ️ Hawthorne Airport: 27 complete years of 28 (1998-2025); incomplete: 1998
- ℹ️ Riverside Airport: 25 complete years of 28 (1998-2025); incomplete: 1998, 2007, 2008
- ℹ️ Torrance Airport: 0 complete years of 0 (None-None); incomplete: none
- ℹ️ Chino Airport: 27 complete years of 28 (1998-2025); incomplete: 1998
- ℹ️ March Air Reserve Base: 84 complete years of 86 (1940-2025); incomplete: 1996, 1999
- ℹ️ San Bernardino Airport: 51 complete years of 59 (1943-2025); incomplete: 1943, 1993, 2016, 2018, 2021, 2022, 2024, 2025
- ℹ️ Long Beach Airport: 74 complete years of 78 (1940-2025); incomplete: 1985, 1986, 1987, 1996
- ℹ️ Van Nuys Airport: 36 complete years of 47 (1943-2025); incomplete: 1945, 1946, 1948, 1950, 1961, 1962, 1973, 1980, 1981, 1984, 1998
- ℹ️ Victorville: 50 complete years of 61 (1942-2025); incomplete: 1946, 1948, 1950, 1973, 1974, 1992, 2005, 2018, 2021, 2023, 2024
- ℹ️ Camarillo Airport: 45 complete years of 51 (1953-2025); incomplete: 1992, 1994, 1995, 1996, 1997, 1998
- ℹ️ Burbank Airport: 80 complete years of 81 (1943-2025); incomplete: 1943
- ℹ️ LAX: 86 complete years of 86 (1940-2025); incomplete: none
- ℹ️ Palmdale Airport: 36 complete years of 40 (1949-2025); incomplete: 1974, 1998, 1999, 2006
- ℹ️ Whiteman Airport (Pacoima): 0 complete years of 0 (None-None); incomplete: none
- ℹ️ Los Alamitos: 16 complete years of 21 (1984-2025); incomplete: 1984, 1989, 1992, 2008, 2020
- ℹ️ Corona Airport: 16 complete years of 20 (2006-2025); incomplete: 2006, 2012, 2019, 2023
- ℹ️ Oxnard Airport: 44 complete years of 49 (1944-2025); incomplete: 1944, 1945, 1952, 1985, 1998
- ℹ️ Point Mugu: 59 complete years of 79 (1947-2025); incomplete: 1947, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2013, 2014, 2016, 2017, 2023
- ℹ️ Downtown LA (USC): 24 complete years of 26 (1999-2024); incomplete: 1999, 2024
- ℹ️ John Wayne Airport: 29 complete years of 36 (1942-2025); incomplete: 1942, 1946, 1974, 1990, 1992, 1996, 1999
- ℹ️ Santa Monica Airport: 25 complete years of 26 (2000-2025); incomplete: 2000
### gaps

- ℹ️ Santa Monica Pier: 1 gap(s) of ≥30 days without TMAX
  - 2019-03-29 → 2019-06-19 (83 days)
- ℹ️ Ontario Airport: 2 gap(s) of ≥30 days without TMAX
  - 1945-11-01 → 1967-12-31 (8096 days)
  - 2001-04-04 → 2001-08-15 (134 days)
- ℹ️ Fullerton Airport: 1 gap(s) of ≥30 days without TMAX
  - 1986-09-02 → 1998-07-01 (4321 days)
- ℹ️ Riverside Airport: 1 gap(s) of ≥30 days without TMAX
  - 2007-07-05 → 2008-07-09 (371 days)
- ℹ️ March Air Reserve Base: 3 gap(s) of ≥30 days without TMAX
  - 1941-08-01 → 1941-08-31 (31 days)
  - 1995-12-31 → 1996-06-30 (183 days)
  - 1999-09-01 → 1999-12-31 (122 days)
- ℹ️ San Bernardino Airport: 2 gap(s) of ≥30 days without TMAX
  - 1971-01-01 → 1972-12-31 (731 days)
  - 1993-04-02 → 2016-06-16 (8477 days)
- ℹ️ Long Beach Airport: 5 gap(s) of ≥30 days without TMAX
  - 1945-07-01 → 1945-07-31 (31 days)
  - 1984-12-01 → 1985-03-31 (121 days)
  - 1986-02-16 → 1987-03-22 (400 days)
  - 1987-03-24 → 1987-11-12 (234 days)
  - 1987-11-14 → 1996-08-31 (3214 days)
- ℹ️ Van Nuys Airport: 8 gap(s) of ≥30 days without TMAX
  - 1945-11-18 → 1946-07-31 (256 days)
  - 1946-10-05 → 1948-04-30 (574 days)
  - 1950-05-25 → 1961-09-30 (4147 days)
  - 1962-08-14 → 1973-04-09 (3892 days)
  - 1980-09-18 → 1980-12-05 (79 days)
  - 1981-09-07 → 1984-07-21 (1049 days)
  - 1984-08-19 → 1984-11-06 (80 days)
  - 1984-11-13 → 1998-05-26 (4943 days)
- ℹ️ Victorville: 11 gap(s) of ≥30 days without TMAX
  - 1946-02-16 → 1948-03-31 (775 days)
  - 1948-11-01 → 1950-09-13 (682 days)
  - 1971-01-01 → 1973-03-05 (795 days)
  - 1973-03-08 → 1973-08-12 (158 days)
  - 1973-08-19 → 1974-02-14 (180 days)
  - 1974-02-17 → 1975-01-14 (332 days)
  - 1992-06-30 → 2005-01-01 (4569 days)
  - 2005-06-17 → 2011-01-04 (2028 days)
- ℹ️ Camarillo Airport: 2 gap(s) of ≥30 days without TMAX
  - 1969-12-16 → 1992-04-08 (8150 days)
  - 1998-10-05 → 1998-11-09 (36 days)
- ℹ️ Burbank Airport: 1 gap(s) of ≥30 days without TMAX
  - 1945-12-20 → 1947-12-31 (742 days)
- ℹ️ Palmdale Airport: 3 gap(s) of ≥30 days without TMAX
  - 1955-01-01 → 1960-12-31 (2192 days)
  - 1965-01-01 → 1972-12-31 (2922 days)
  - 1974-04-16 → 1998-04-08 (8759 days)
- ℹ️ Los Alamitos: 4 gap(s) of ≥30 days without TMAX
  - 1984-08-15 → 1989-10-17 (1890 days)
  - 1989-10-19 → 1992-04-30 (925 days)
  - 1992-05-05 → 2008-04-23 (5833 days)
  - 2020-06-04 → 2020-10-15 (134 days)
- ℹ️ Corona Airport: 2 gap(s) of ≥30 days without TMAX
  - 2012-12-03 → 2013-01-15 (44 days)
  - 2018-12-13 → 2019-01-22 (41 days)
- ℹ️ Oxnard Airport: 3 gap(s) of ≥30 days without TMAX
  - 1945-08-01 → 1952-12-09 (2688 days)
  - 1969-12-16 → 1985-04-29 (5614 days)
  - 1985-05-01 → 1998-03-04 (4691 days)
- ℹ️ Point Mugu: 55 gap(s) of ≥30 days without TMAX
  - 1993-05-02 → 1993-07-27 (87 days)
  - 1993-07-30 → 1993-11-18 (112 days)
  - 1994-01-05 → 1994-02-25 (52 days)
  - 1994-03-01 → 1994-06-25 (117 days)
  - 1994-06-29 → 1994-10-04 (98 days)
  - 1994-11-03 → 1995-01-06 (65 days)
  - 1995-01-26 → 1995-03-08 (42 days)
  - 1995-04-07 → 1995-08-07 (123 days)
- ℹ️ John Wayne Airport: 5 gap(s) of ≥30 days without TMAX
  - 1946-02-01 → 1974-08-08 (10416 days)
  - 1974-08-10 → 1990-08-14 (5849 days)
  - 1990-08-16 → 1992-04-30 (624 days)
  - 1992-05-03 → 1996-03-06 (1404 days)
  - 1996-03-08 → 1999-02-17 (1077 days)
### manifests

- ℹ️ all raw files match their manifest
### obs_time

- ℹ️ Santa Monica Pier: 2009-05-08→2025-12-30 2400
- ℹ️ Ontario Airport: 1943-01-01→2025-12-30 2400
- ℹ️ Fullerton Airport: 1986-09-01→2025-12-30 2400
- ℹ️ Hawthorne Airport: 1998-11-11→2025-12-30 2400
- ℹ️ Riverside Airport: 1998-07-24→2025-12-30 2400
- ℹ️ Torrance Airport: 
- ℹ️ Chino Airport: 1998-05-22→2025-12-25 2400
- ℹ️ March Air Reserve Base: 1940-01-01→2025-12-30 2400
- ℹ️ San Bernardino Airport: 1943-03-17→2025-12-30 2400
- ℹ️ Long Beach Airport: 1940-01-01→2025-12-30 2400
- ℹ️ Van Nuys Airport: 1943-01-01→2025-12-30 2400
- ℹ️ Victorville: 1942-02-03→2026-08-24 2400
- ℹ️ Camarillo Airport: 1953-01-09→2025-12-30 2400
- ℹ️ Burbank Airport: 1943-06-01→2025-12-30 2400
- ℹ️ LAX: 1940-01-01→2025-12-30 2400
- ℹ️ Palmdale Airport: 1949-01-01→2025-12-30 2400
- ℹ️ Whiteman Airport (Pacoima): 
- ℹ️ Los Alamitos: 1984-07-10→2025-12-30 2400
- ℹ️ Corona Airport: 2006-09-08→2025-12-30 2400
- ℹ️ Oxnard Airport: 1944-04-01→2025-12-30 2400
- ℹ️ Point Mugu: 1947-11-13→2025-12-30 2400
- ℹ️ Downtown LA (USC): 1999-07-01→2024-05-19 2400
- ℹ️ John Wayne Airport: 1942-10-06→2025-12-30 2400
- ℹ️ Santa Monica Airport: 2000-10-06→2025-12-30 2400
### station_config

- ℹ️ **2024** Downtown LA (USC): hourly record ended 2024
