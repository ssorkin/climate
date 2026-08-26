# Data Quality Report

Generated 2026-08-26 by `clim check`. Problems in the source data are surfaced here and in `known_issues/`, never silently patched. Anomalies block the nightly deploy.

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

- 🟡 **2024** Mt. Wilson: 2024 has 143/366 TMAX and 141/366 TMIN days
- 🟡 **2025** Mt. Wilson: 2025 has 290/365 TMAX and 289/365 TMIN days
### freshness

- 🟡 **2026** Mt. Wilson: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Newport Beach: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Palmdale: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Pasadena: last TMAX is 2026-07-29 (28 days ago)
- 🟡 **2026** Santa Ana: last TMAX is 2026-07-31 (26 days ago)
### suspicious_values

- 🟡 Culver City: 4 suspicious unflagged value(s)
  - 7 identical TMAX values from 2001-10-22
  - 9 identical TMAX values from 2011-08-09
  - 7 identical TMAX values from 2018-06-25
  - 7 identical TMAX values from 2021-06-04
- 🟡 Newport Beach: 11 suspicious unflagged value(s)
  - 9 identical TMAX values from 1968-07-31
  - 7 identical TMAX values from 1991-05-19
  - 7 identical TMAX values from 1996-05-25
  - 7 identical TMAX values from 1996-08-04
  - 7 identical TMAX values from 2002-10-27
  - 7 identical TMAX values from 2016-05-22
  - 8 identical TMAX values from 2019-07-10
  - 7 identical TMAX values from 2020-07-14
- 🟡 Palmdale: 1 suspicious unflagged value(s)
  - 7 identical TMAX values from 2013-10-22
- 🟡 UCLA: 2 suspicious unflagged value(s)
  - 7 identical TMAX values from 2024-01-08
  - 8 identical TMAX values from 2024-05-18
- 🟡 Torrance Airport: 1 suspicious unflagged value(s)
  - 7 identical TMAX values from 1999-10-11
- 🟡 LAX: 3 suspicious unflagged value(s)
  - 7 identical TMAX values from 1956-06-04
  - 7 identical TMAX values from 2009-06-18
  - 7 identical TMAX values from 2012-07-22
### completeness

- ℹ️ Burbank: 66 complete years of 87 (1939-2025); incomplete: 1939, 1966, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1996, 1999, 2000, 2003, 2006, 2007, 2008, 2009, 2010, 2011
- ℹ️ Culver City: 58 complete years of 91 (1935-2025); incomplete: 1937, 1938, 1939, 1940, 1941, 1967, 1968, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1991, 1992, 1993, 1994, 2002, 2004, 2005, 2006, 2007, 2008, 2010, 2011, 2014
- ℹ️ Mt. Wilson: 51 complete years of 71 (1948-2025); incomplete: 1948, 1978, 1986, 1987, 1988, 1990, 1991, 1992, 1993, 1994, 1998, 1999, 2000, 2003, 2004, 2005, 2010, 2011, 2024, 2025
- ℹ️ Newport Beach: 88 complete years of 105 (1921-2025); incomplete: 1921, 1922, 1923, 1928, 1929, 1941, 1987, 1989, 1991, 1994, 1998, 2000, 2006, 2007, 2008, 2009, 2010
- ℹ️ Palmdale: 90 complete years of 108 (1903-2025); incomplete: 1903, 1919, 1920, 1921, 1922, 1923, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931, 1932, 1961, 2008, 2020
- ℹ️ Pasadena: 118 complete years of 123 (1893-2025); incomplete: 1894, 1895, 1906, 1907, 1908
- ℹ️ Santa Ana: 83 complete years of 119 (1906-2025); incomplete: 1906, 1907, 1908, 1909, 1910, 1912, 1913, 1914, 1915, 1916, 1919, 1920, 1921, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931, 1932, 1933, 1934, 1935, 1937, 1938, 1939, 1940, 1941, 1975, 1976, 1990, 2005, 2006, 2009
- ℹ️ UCLA: 86 complete years of 93 (1933-2025); incomplete: 1933, 1935, 1936, 1938, 1941, 1945, 1978
- ℹ️ Woodland Hills: 55 complete years of 77 (1949-2025); incomplete: 1949, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1991, 1993, 1994, 1997, 1998, 1999, 2000, 2001, 2004, 2005, 2006, 2009, 2010, 2011
- ℹ️ Torrance Airport: 84 complete years of 94 (1932-2025); incomplete: 1932, 1955, 1957, 1961, 2005, 2006, 2007, 2008, 2009, 2011
- ℹ️ Long Beach Airport: 75 complete years of 77 (1949-2025); incomplete: 1957, 1958
- ℹ️ LAX: 81 complete years of 82 (1944-2025); incomplete: 1944
### duplicates

- ℹ️ no duplicate rows
### gaps

- ℹ️ Burbank: 9 gap(s) of ≥30 days without TMAX
  - 1943-11-01 → 1943-11-30 (30 days)
  - 1966-07-01 → 1966-09-30 (92 days)
  - 1976-03-01 → 1976-03-31 (31 days)
  - 1979-05-01 → 1979-05-31 (31 days)
  - 1993-10-01 → 1993-10-31 (31 days)
  - 2000-10-01 → 2000-10-31 (31 days)
  - 2003-04-01 → 2003-04-30 (30 days)
  - 2003-09-01 → 2003-09-30 (30 days)
- ℹ️ Culver City: 25 gap(s) of ≥30 days without TMAX
  - 1941-01-01 → 1941-02-28 (59 days)
  - 1941-04-01 → 1941-04-30 (30 days)
  - 1948-06-01 → 1948-06-30 (30 days)
  - 1967-07-01 → 1967-08-09 (40 days)
  - 1968-07-01 → 1968-07-31 (31 days)
  - 1968-09-01 → 1968-09-30 (30 days)
  - 1976-12-01 → 1976-12-31 (31 days)
  - 1977-12-01 → 1977-12-31 (31 days)
- ℹ️ Mt. Wilson: 11 gap(s) of ≥30 days without TMAX
  - 1973-09-01 → 1973-09-30 (30 days)
  - 1982-06-01 → 1982-06-30 (30 days)
  - 1986-06-01 → 1987-04-30 (334 days)
  - 2000-06-01 → 2000-06-30 (30 days)
  - 2003-06-01 → 2003-06-30 (30 days)
  - 2003-12-01 → 2003-12-31 (31 days)
  - 2010-04-01 → 2010-04-30 (30 days)
  - 2011-08-01 → 2011-10-31 (92 days)
- ℹ️ Newport Beach: 18 gap(s) of ≥30 days without TMAX
  - 1922-04-13 → 1922-05-31 (49 days)
  - 1923-11-01 → 1924-01-31 (92 days)
  - 1928-07-01 → 1929-03-31 (274 days)
  - 1941-01-01 → 1941-02-28 (59 days)
  - 1941-04-01 → 1941-04-30 (30 days)
  - 1948-06-01 → 1948-06-30 (30 days)
  - 1981-04-01 → 1981-04-30 (30 days)
  - 1987-09-01 → 1987-09-30 (30 days)
- ℹ️ Palmdale: 3 gap(s) of ≥30 days without TMAX
  - 1931-10-01 → 1932-08-14 (319 days)
  - 1961-07-17 → 1961-08-30 (45 days)
  - 2020-06-01 → 2020-07-12 (42 days)
- ℹ️ Pasadena: 7 gap(s) of ≥30 days without TMAX
  - 1893-07-01 → 1893-07-31 (31 days)
  - 1894-03-01 → 1894-06-30 (122 days)
  - 1895-05-01 → 1895-06-30 (61 days)
  - 1895-10-01 → 1908-05-05 (4600 days)
  - 1973-11-01 → 1973-11-30 (30 days)
  - 1978-04-01 → 1978-04-30 (30 days)
  - 1979-03-01 → 1979-03-31 (31 days)
- ℹ️ Santa Ana: 6 gap(s) of ≥30 days without TMAX
  - 1919-10-01 → 1919-10-31 (31 days)
  - 1920-04-01 → 1920-04-30 (30 days)
  - 1990-03-01 → 1990-03-31 (31 days)
  - 2005-10-01 → 2005-10-31 (31 days)
  - 2006-03-01 → 2006-03-31 (31 days)
  - 2009-07-01 → 2009-07-31 (31 days)
- ℹ️ UCLA: 9 gap(s) of ≥30 days without TMAX
  - 1935-07-01 → 1935-07-31 (31 days)
  - 1936-05-01 → 1936-05-31 (31 days)
  - 1941-01-01 → 1941-02-28 (59 days)
  - 1941-04-01 → 1941-04-30 (30 days)
  - 1942-09-01 → 1942-09-30 (30 days)
  - 1977-12-01 → 1978-01-31 (62 days)
  - 1978-03-01 → 1978-04-30 (61 days)
  - 1980-01-01 → 1980-01-31 (31 days)
- ℹ️ Woodland Hills: 1 gap(s) of ≥30 days without TMAX
  - 2000-10-01 → 2000-10-31 (31 days)
- ℹ️ Torrance Airport: 20 gap(s) of ≥30 days without TMAX
  - 1932-08-31 → 1932-09-30 (31 days)
  - 1941-08-01 → 1941-08-31 (31 days)
  - 1957-05-22 → 1957-06-25 (35 days)
  - 1968-10-01 → 1968-10-31 (31 days)
  - 1970-08-01 → 1970-08-31 (31 days)
  - 1982-09-01 → 1982-09-30 (30 days)
  - 2005-06-01 → 2005-06-30 (30 days)
  - 2006-03-01 → 2006-03-31 (31 days)
- ℹ️ Long Beach Airport: 1 gap(s) of ≥30 days without TMAX
  - 1957-10-01 → 1958-03-31 (182 days)
### manifests

- ℹ️ all raw files match their manifest
### obs_time

- ℹ️ Burbank: 1939-12-01→1966-06-30 n/a; 1966-10-01→1985-04-29 1630; 1985-04-30→1994-03-31 1700; 1994-04-01→2026-08-23 0700
- ℹ️ Culver City: 1935-01-04→1995-12-31 1700; 1996-01-01→2026-08-23 1600
- ℹ️ Mt. Wilson: 1948-07-01→2003-05-31 1500; 2003-07-01→2016-12-26 2400; 2024-07-01→2026-07-31 n/a
- ℹ️ Newport Beach: 1921-01-01→1953-10-31 n/a; 1953-11-01→2017-07-18 1700; 2017-07-19→2026-07-31 1530
- ℹ️ Palmdale: 1931-04-01→2014-04-24 1700; 2014-04-25→2026-07-31 1600
- ℹ️ Pasadena: 1893-01-01→1930-12-31 n/a; 1931-01-01→2015-08-05 1600; 2015-08-06→2026-07-29 0800
- ℹ️ Santa Ana: 1916-05-17→1930-12-31 n/a; 1931-01-01→2026-07-31 1600
- ℹ️ UCLA: 1933-03-01→2026-08-23 1600
- ℹ️ Woodland Hills: 1949-07-01→2026-08-21 1600
- ℹ️ Torrance Airport: 1932-01-01→1945-12-31 n/a; 1946-01-01→1955-09-13 1700; 1955-09-19→1958-12-18 1535; 1958-12-19→1962-01-09 1700; 1962-01-14→2026-08-23 1600
- ℹ️ Long Beach Airport: 1949-01-01→1976-07-15 n/a; 1976-07-16→2026-08-23 2400
- ℹ️ LAX: 1944-08-01→1967-12-31 2400; 1968-01-01→1968-05-28 n/a; 1968-05-29→2026-08-23 2400
### qflags

- ℹ️ Burbank: 1122 flagged TMAX/TMIN values withheld I=1086, O=4, S=12, Z=20
- ℹ️ Culver City: 678 flagged TMAX/TMIN values withheld G=2, I=643, O=20, S=13
- ℹ️ Mt. Wilson: 665 flagged TMAX/TMIN values withheld I=654, S=11
- ℹ️ Newport Beach: 544 flagged TMAX/TMIN values withheld G=4, I=526, O=8, S=6
- ℹ️ Palmdale: 408 flagged TMAX/TMIN values withheld G=1, I=375, O=1, S=31
- ℹ️ Pasadena: 152 flagged TMAX/TMIN values withheld G=1, I=139, S=12
- ℹ️ Santa Ana: 1647 flagged TMAX/TMIN values withheld G=2, I=1612, O=2, S=31
- ℹ️ UCLA: 309 flagged TMAX/TMIN values withheld I=296, O=10, S=3
- ℹ️ Woodland Hills: 1413 flagged TMAX/TMIN values withheld I=1394, S=19
- ℹ️ Torrance Airport: 228 flagged TMAX/TMIN values withheld G=1, I=178, O=25, S=24
- ℹ️ Long Beach Airport: 1 flagged TMAX/TMIN values withheld S=1
- ℹ️ LAX: 4 flagged TMAX/TMIN values withheld O=4
### station_config

- ℹ️ all stations present with TMAX/TMIN
### whole_degree_f

- ℹ️ ≥99.5% of values round-trip to whole °F everywhere
