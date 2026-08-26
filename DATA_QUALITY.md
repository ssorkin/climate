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
- 🟡 **2021** Riverside: 2021 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2022** Riverside: 2022 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2023** Riverside: 2023 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2024** Riverside: 2024 has 0/366 TMAX and 0/366 TMIN days
- 🟡 **2025** Riverside: 2025 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2021** San Gabriel: 2021 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2022** San Gabriel: 2022 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2023** San Gabriel: 2023 has 0/365 TMAX and 0/365 TMIN days
- 🟡 **2024** San Gabriel: 2024 has 0/366 TMAX and 0/366 TMIN days
- 🟡 **2025** San Gabriel: 2025 has 0/365 TMAX and 0/365 TMIN days
### freshness

- 🟡 **1980** Claremont: last TMAX is 1980-12-31 (16674 days ago)
- 🟡 **1988** Corona: last TMAX is 1988-07-31 (13905 days ago)
- 🟡 **2026** Lake Elsinore: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2008** Laguna Beach: last TMAX is 2008-07-17 (6614 days ago)
- 🟡 **2026** Mt. Wilson: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Newport Beach: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Palmdale: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2026** Pasadena: last TMAX is 2026-07-29 (28 days ago)
- 🟡 **2012** Pomona Fairplex: last TMAX is 2012-09-30 (5078 days ago)
- 🟡 **2016** Riverside: last TMAX is 2016-11-21 (3565 days ago)
- 🟡 **2009** Riverside Citrus Station: last TMAX is 2009-09-30 (6174 days ago)
- 🟡 **1974** San Fernando: last TMAX is 1974-03-19 (19153 days ago)
- 🟡 **2015** San Gabriel: last TMAX is 2015-03-31 (4166 days ago)
- 🟡 **2026** Santa Ana: last TMAX is 2026-07-31 (26 days ago)
- 🟡 **2010** Santa Monica Pier: last TMAX is 2010-02-28 (6023 days ago)
- 🟡 **2003** Tustin Irvine Ranch: last TMAX is 2003-06-30 (8458 days ago)
- 🟡 **2007** Yorba Linda: last TMAX is 2007-06-30 (6997 days ago)
- 🟡 **1998** El Toro MCAS: last TMAX is 1998-12-10 (10121 days ago)
### station_config

- 🟡 **1980** Claremont: TMAX inventory ends 1980
- 🟡 **1980** Claremont: TMIN inventory ends 1980
- 🟡 **1988** Corona: TMAX inventory ends 1988
- 🟡 **1988** Corona: TMIN inventory ends 1988
- 🟡 **2008** Laguna Beach: TMAX inventory ends 2008
- 🟡 **2008** Laguna Beach: TMIN inventory ends 2008
- 🟡 **2012** Pomona Fairplex: TMAX inventory ends 2012
- 🟡 **2012** Pomona Fairplex: TMIN inventory ends 2012
- 🟡 **2016** Riverside: TMAX inventory ends 2016
- 🟡 **2016** Riverside: TMIN inventory ends 2016
- 🟡 **2009** Riverside Citrus Station: TMAX inventory ends 2009
- 🟡 **2009** Riverside Citrus Station: TMIN inventory ends 2009
- 🟡 **1974** San Fernando: TMAX inventory ends 1974
- 🟡 **1974** San Fernando: TMIN inventory ends 1974
- 🟡 **2014** San Gabriel: TMIN inventory ends 2014
- 🟡 **2015** San Gabriel: TMAX inventory ends 2015
- 🟡 **2010** Santa Monica Pier: TMAX inventory ends 2010
- 🟡 **2010** Santa Monica Pier: TMIN inventory ends 2010
- 🟡 **2003** Tustin Irvine Ranch: TMAX inventory ends 2003
- 🟡 **2003** Tustin Irvine Ranch: TMIN inventory ends 2003
- 🟡 **2007** Yorba Linda: TMAX inventory ends 2007
- 🟡 **2007** Yorba Linda: TMIN inventory ends 2007
- 🟡 **1998** El Toro MCAS: TMAX inventory ends 1998
- 🟡 **1998** El Toro MCAS: TMIN inventory ends 1998
### suspicious_values

- 🟡 Culver City: 4 suspicious unflagged value(s)
  - 7 identical TMAX values from 2001-10-22
  - 9 identical TMAX values from 2011-08-09
  - 7 identical TMAX values from 2018-06-25
  - 7 identical TMAX values from 2021-06-04
- 🟡 Lake Elsinore: 1 suspicious unflagged value(s)
  - 8 identical TMAX values from 1996-07-08
- 🟡 Laguna Beach: 3 suspicious unflagged value(s)
  - 7 identical TMAX values from 1958-03-24
  - 7 identical TMAX values from 1974-03-27
  - 7 identical TMAX values from 1986-08-07
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
- 🟡 San Fernando: 1 suspicious unflagged value(s)
  - 7 identical TMAX values from 1939-07-28
- 🟡 Santa Monica Pier: 14 suspicious unflagged value(s)
  - 9 identical TMAX values from 1961-07-19
  - 7 identical TMAX values from 1963-06-15
  - 7 identical TMAX values from 1965-05-26
  - 7 identical TMAX values from 1966-04-07
  - 7 identical TMAX values from 1973-07-29
  - 8 identical TMAX values from 1986-07-08
  - 7 identical TMAX values from 1993-07-16
  - 10 identical TMAX values from 1993-08-07
- 🟡 UCLA: 2 suspicious unflagged value(s)
  - 7 identical TMAX values from 2024-01-08
  - 8 identical TMAX values from 2024-05-18
- 🟡 Yorba Linda: 1 suspicious unflagged value(s)
  - 18 identical TMAX values from 2003-07-20
- 🟡 Torrance Airport: 1 suspicious unflagged value(s)
  - 7 identical TMAX values from 1999-10-11
- 🟡 LAX: 3 suspicious unflagged value(s)
  - 7 identical TMAX values from 1956-06-04
  - 7 identical TMAX values from 2009-06-18
  - 7 identical TMAX values from 2012-07-22
- 🟡 Palmdale Airport: 1 suspicious unflagged value(s)
  - jump on 1948-07-01: tmax=367 tmin=167
### completeness

- ℹ️ Burbank: 66 complete years of 87 (1939-2025); incomplete: 1939, 1966, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1996, 1999, 2000, 2003, 2006, 2007, 2008, 2009, 2010, 2011
- ℹ️ Claremont: 73 complete years of 87 (1893-1980); incomplete: 1895, 1898, 1906, 1907, 1909, 1910, 1911, 1924, 1926, 1931, 1957, 1959, 1966, 1968
- ℹ️ Corona: 71 complete years of 81 (1908-1988); incomplete: 1908, 1909, 1910, 1911, 1912, 1913, 1922, 1948, 1955, 1988
- ℹ️ Culver City: 58 complete years of 91 (1935-2025); incomplete: 1937, 1938, 1939, 1940, 1941, 1967, 1968, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1991, 1992, 1993, 1994, 2002, 2004, 2005, 2006, 2007, 2008, 2010, 2011, 2014
- ℹ️ Lake Elsinore: 91 complete years of 127 (1897-2025); incomplete: 1897, 1903, 1912, 1915, 1947, 1948, 1951, 1967, 1970, 1971, 1975, 1976, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1987, 1988, 1989, 1990, 1993, 1994, 1997, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2018, 2019
- ℹ️ Laguna Beach: 54 complete years of 81 (1928-2008); incomplete: 1928, 1937, 1939, 1941, 1942, 1943, 1945, 1946, 1947, 1950, 1951, 1957, 1958, 1959, 1968, 1978, 1979, 1980, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 2006, 2008
- ℹ️ Mt. Wilson: 51 complete years of 71 (1948-2025); incomplete: 1948, 1978, 1986, 1987, 1988, 1990, 1991, 1992, 1993, 1994, 1998, 1999, 2000, 2003, 2004, 2005, 2010, 2011, 2024, 2025
- ℹ️ Newport Beach: 88 complete years of 105 (1921-2025); incomplete: 1921, 1922, 1923, 1928, 1929, 1941, 1987, 1989, 1991, 1994, 1998, 2000, 2006, 2007, 2008, 2009, 2010
- ℹ️ Palmdale: 90 complete years of 108 (1903-2025); incomplete: 1903, 1919, 1920, 1921, 1922, 1923, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931, 1932, 1961, 2008, 2020
- ℹ️ Pasadena: 118 complete years of 123 (1893-2025); incomplete: 1894, 1895, 1906, 1907, 1908
- ℹ️ Pomona Fairplex: 78 complete years of 108 (1893-2012); incomplete: 1893, 1895, 1906, 1907, 1908, 1945, 1946, 1947, 1948, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1990, 1991, 1992, 1993, 1994, 1995, 2001, 2002, 2004, 2006, 2008, 2009, 2010, 2012
- ℹ️ Riverside: 104 complete years of 128 (1893-2025); incomplete: 1896, 1901, 1947, 1992, 2001, 2002, 2004, 2005, 2006, 2007, 2008, 2009, 2011, 2012, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
- ℹ️ Riverside Citrus Station: 53 complete years of 58 (1948-2009); incomplete: 1948, 1949, 1950, 1951, 2009
- ℹ️ San Fernando: 53 complete years of 69 (1906-1974); incomplete: 1906, 1907, 1908, 1909, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917, 1918, 1920, 1963, 1974
- ℹ️ San Gabriel: 61 complete years of 86 (1939-2025); incomplete: 1939, 1941, 1943, 1998, 1999, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2010, 2012, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
- ℹ️ Santa Ana: 83 complete years of 119 (1906-2025); incomplete: 1906, 1907, 1908, 1909, 1910, 1912, 1913, 1914, 1915, 1916, 1919, 1920, 1921, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931, 1932, 1933, 1934, 1935, 1937, 1938, 1939, 1940, 1941, 1975, 1976, 1990, 2005, 2006, 2009
- ℹ️ Santa Monica Pier: 54 complete years of 74 (1937-2010); incomplete: 1937, 1938, 1940, 1942, 1949, 1973, 1978, 1979, 1980, 1981, 1982, 1983, 1996, 2001, 2005, 2006, 2007, 2008, 2009, 2010
- ℹ️ Tustin Irvine Ranch: 77 complete years of 102 (1902-2003); incomplete: 1902, 1903, 1904, 1905, 1906, 1907, 1908, 1909, 1910, 1911, 1912, 1913, 1914, 1943, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1995, 2001, 2003
- ℹ️ UCLA: 86 complete years of 93 (1933-2025); incomplete: 1933, 1935, 1936, 1938, 1941, 1945, 1978
- ℹ️ Woodland Hills: 55 complete years of 77 (1949-2025); incomplete: 1949, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1991, 1993, 1994, 1997, 1998, 1999, 2000, 2001, 2004, 2005, 2006, 2009, 2010, 2011
- ℹ️ Yorba Linda: 62 complete years of 78 (1912-2007); incomplete: 1912, 1942, 1943, 1944, 1945, 1947, 1949, 1950, 1964, 1966, 1967, 1969, 1982, 2001, 2005, 2007
- ℹ️ Torrance Airport: 84 complete years of 94 (1932-2025); incomplete: 1932, 1955, 1957, 1961, 2005, 2006, 2007, 2008, 2009, 2011
- ℹ️ Long Beach Airport: 75 complete years of 77 (1949-2025); incomplete: 1957, 1958
- ℹ️ LAX: 81 complete years of 82 (1944-2025); incomplete: 1944
- ℹ️ Palmdale Airport: 60 complete years of 63 (1934-2025); incomplete: 1948, 1974, 1998
- ℹ️ El Toro MCAS: 51 complete years of 54 (1945-1998); incomplete: 1945, 1980, 1998
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
- ℹ️ Claremont: 13 gap(s) of ≥30 days without TMAX
  - 1895-12-01 → 1895-12-31 (31 days)
  - 1906-03-01 → 1906-03-31 (31 days)
  - 1907-07-31 → 1907-08-31 (32 days)
  - 1924-06-01 → 1924-07-31 (61 days)
  - 1926-10-01 → 1926-11-30 (61 days)
  - 1931-05-01 → 1931-06-30 (61 days)
  - 1957-08-01 → 1957-09-01 (32 days)
  - 1958-01-01 → 1958-12-31 (365 days)
- ℹ️ Corona: 7 gap(s) of ≥30 days without TMAX
  - 1914-04-01 → 1914-04-30 (30 days)
  - 1916-07-01 → 1916-07-31 (31 days)
  - 1918-12-01 → 1919-01-31 (62 days)
  - 1922-01-30 → 1922-02-28 (30 days)
  - 1937-11-01 → 1937-11-30 (30 days)
  - 1948-01-01 → 1948-06-30 (182 days)
  - 1955-04-21 → 1955-05-24 (34 days)
- ℹ️ Culver City: 25 gap(s) of ≥30 days without TMAX
  - 1941-01-01 → 1941-02-28 (59 days)
  - 1941-04-01 → 1941-04-30 (30 days)
  - 1948-06-01 → 1948-06-30 (30 days)
  - 1967-07-01 → 1967-08-09 (40 days)
  - 1968-07-01 → 1968-07-31 (31 days)
  - 1968-09-01 → 1968-09-30 (30 days)
  - 1976-12-01 → 1976-12-31 (31 days)
  - 1977-12-01 → 1977-12-31 (31 days)
- ℹ️ Lake Elsinore: 29 gap(s) of ≥30 days without TMAX
  - 1898-03-01 → 1898-03-31 (31 days)
  - 1903-07-01 → 1903-08-31 (62 days)
  - 1912-11-01 → 1915-03-31 (881 days)
  - 1924-08-01 → 1924-08-31 (31 days)
  - 1947-10-01 → 1948-08-05 (310 days)
  - 1970-08-01 → 1970-09-01 (32 days)
  - 1975-11-01 → 1975-11-30 (30 days)
  - 1976-01-01 → 1976-01-31 (31 days)
- ℹ️ Laguna Beach: 12 gap(s) of ≥30 days without TMAX
  - 1941-07-01 → 1941-07-31 (31 days)
  - 1942-11-01 → 1942-11-30 (30 days)
  - 1943-08-15 → 1943-12-14 (122 days)
  - 1946-12-01 → 1946-12-31 (31 days)
  - 1956-12-02 → 1957-01-14 (44 days)
  - 1978-11-01 → 1978-11-30 (30 days)
  - 1979-08-18 → 1979-10-31 (75 days)
  - 1980-01-01 → 1980-01-31 (31 days)
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
- ℹ️ Pomona Fairplex: 13 gap(s) of ≥30 days without TMAX
  - 1894-04-01 → 1894-04-30 (30 days)
  - 1895-10-01 → 1895-11-30 (61 days)
  - 1903-01-01 → 1912-12-31 (3653 days)
  - 1950-03-01 → 1950-03-31 (31 days)
  - 1951-03-01 → 1951-03-31 (31 days)
  - 1994-06-01 → 1994-08-31 (92 days)
  - 1995-05-31 → 2000-12-31 (2042 days)
  - 2001-06-01 → 2001-06-30 (30 days)
- ℹ️ Riverside: 6 gap(s) of ≥30 days without TMAX
  - 1893-08-01 → 1893-08-31 (31 days)
  - 1896-02-01 → 1901-08-05 (2012 days)
  - 1992-08-31 → 1992-09-30 (31 days)
  - 2001-01-01 → 2001-02-02 (33 days)
  - 2006-03-01 → 2006-03-31 (31 days)
  - 2009-07-01 → 2010-12-31 (549 days)
- ℹ️ Riverside Citrus Station: 3 gap(s) of ≥30 days without TMAX
  - 2000-01-01 → 2000-01-31 (31 days)
  - 2001-03-01 → 2001-03-31 (31 days)
  - 2006-06-01 → 2006-06-30 (30 days)
- ℹ️ San Fernando: 4 gap(s) of ≥30 days without TMAX
  - 1918-10-01 → 1918-10-31 (31 days)
  - 1920-01-01 → 1920-01-31 (31 days)
  - 1939-09-01 → 1939-09-30 (30 days)
  - 1951-04-01 → 1951-04-30 (30 days)
- ℹ️ San Gabriel: 13 gap(s) of ≥30 days without TMAX
  - 1941-01-01 → 1941-02-28 (59 days)
  - 1941-04-01 → 1941-04-30 (30 days)
  - 1943-01-01 → 1943-03-31 (90 days)
  - 1973-01-01 → 1973-01-31 (31 days)
  - 2001-03-01 → 2001-03-31 (31 days)
  - 2002-03-01 → 2002-03-31 (31 days)
  - 2002-09-30 → 2002-10-31 (32 days)
  - 2004-06-01 → 2004-06-30 (30 days)
- ℹ️ Santa Ana: 6 gap(s) of ≥30 days without TMAX
  - 1919-10-01 → 1919-10-31 (31 days)
  - 1920-04-01 → 1920-04-30 (30 days)
  - 1990-03-01 → 1990-03-31 (31 days)
  - 2005-10-01 → 2005-10-31 (31 days)
  - 2006-03-01 → 2006-03-31 (31 days)
  - 2009-07-01 → 2009-07-31 (31 days)
- ℹ️ Santa Monica Pier: 33 gap(s) of ≥30 days without TMAX
  - 1938-11-19 → 1939-01-01 (44 days)
  - 1940-09-01 → 1940-12-31 (122 days)
  - 1942-03-01 → 1942-03-31 (31 days)
  - 1949-01-01 → 1949-04-30 (120 days)
  - 1968-11-01 → 1968-11-30 (30 days)
  - 1973-04-01 → 1973-05-31 (61 days)
  - 1973-09-01 → 1973-09-30 (30 days)
  - 1973-12-01 → 1974-01-08 (39 days)
- ℹ️ Tustin Irvine Ranch: 6 gap(s) of ≥30 days without TMAX
  - 1926-10-01 → 1926-10-31 (31 days)
  - 1943-05-01 → 1943-06-23 (54 days)
  - 1964-06-01 → 1964-06-30 (30 days)
  - 1980-05-31 → 1980-06-30 (31 days)
  - 1986-11-01 → 1986-11-30 (30 days)
  - 1995-07-01 → 1995-09-30 (92 days)
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
- ℹ️ Yorba Linda: 15 gap(s) of ≥30 days without TMAX
  - 1913-09-01 → 1913-09-30 (30 days)
  - 1920-04-01 → 1920-04-30 (30 days)
  - 1943-03-01 → 1943-03-31 (31 days)
  - 1943-11-01 → 1943-11-30 (30 days)
  - 1944-05-01 → 1944-06-30 (61 days)
  - 1944-10-01 → 1945-03-02 (153 days)
  - 1949-10-01 → 1950-03-14 (165 days)
  - 1964-08-01 → 1964-10-04 (65 days)
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
- ℹ️ Palmdale Airport: 3 gap(s) of ≥30 days without TMAX
  - 1942-01-01 → 1948-06-30 (2373 days)
  - 1974-04-01 → 1998-04-12 (8778 days)
  - 2021-11-01 → 2021-11-30 (30 days)
- ℹ️ El Toro MCAS: 1 gap(s) of ≥30 days without TMAX
  - 1980-01-01 → 1980-02-29 (60 days)
### manifests

- ℹ️ all raw files match their manifest
### obs_time

- ℹ️ Burbank: 1939-12-01→1966-06-30 n/a; 1966-10-01→1985-04-29 1630; 1985-04-30→1994-03-31 1700; 1994-04-01→2026-08-23 0700
- ℹ️ Claremont: 1893-02-01→1930-12-31 n/a; 1931-01-01→1980-12-31 0800
- ℹ️ Corona: 1913-11-22→1975-02-05 n/a; 1975-02-06→1988-07-31 1700
- ℹ️ Culver City: 1935-01-04→1995-12-31 1700; 1996-01-01→2026-08-23 1600
- ℹ️ Lake Elsinore: 1897-03-10→1930-12-31 n/a; 1931-01-01→2026-07-31 1700
- ℹ️ Laguna Beach: 1928-03-01→1930-12-31 n/a; 1931-01-01→2008-07-17 1600
- ℹ️ Mt. Wilson: 1948-07-01→2003-05-31 1500; 2003-07-01→2016-12-26 2400; 2024-07-01→2026-07-31 n/a
- ℹ️ Newport Beach: 1921-01-01→1953-10-31 n/a; 1953-11-01→2017-07-18 1700; 2017-07-19→2026-07-31 1530
- ℹ️ Palmdale: 1931-04-01→2014-04-24 1700; 2014-04-25→2026-07-31 1600
- ℹ️ Pasadena: 1893-01-01→1930-12-31 n/a; 1931-01-01→2015-08-05 1600; 2015-08-06→2026-07-29 0800
- ℹ️ Pomona Fairplex: 1893-12-17→1930-12-31 n/a; 1931-01-01→1963-04-21 0630; 1963-04-22→1969-12-31 1700; 1970-01-01→1995-05-30 1600; 2001-01-01→2012-09-30 2400
- ℹ️ Riverside: 1893-01-01→1930-12-31 n/a; 1931-01-01→1992-07-20 1700; 1992-07-21→1992-08-30 n/a; 1992-10-01→2016-11-21 1700
- ℹ️ Riverside Citrus Station: 1956-01-02→1956-12-31 2400; 1957-01-01→1960-04-30 n/a; 1960-05-01→2009-09-30 2400
- ℹ️ San Fernando: 1918-06-01→1930-12-31 n/a; 1931-01-01→1951-12-31 1700; 1952-01-01→1956-06-30 n/a; 1956-07-01→1974-03-19 1700
- ℹ️ San Gabriel: 1939-05-01→2010-02-11 1600; 2010-02-12→2015-03-31 2400
- ℹ️ Santa Ana: 1916-05-17→1930-12-31 n/a; 1931-01-01→2026-07-31 1600
- ℹ️ Santa Monica Pier: 1937-01-12→1937-08-31 n/a; 1937-09-01→1986-01-27 1600; 1986-01-29→1999-04-09 n/a; 1999-04-16→2008-05-31 1600; 2008-08-01→2010-02-28 2400
- ℹ️ Tustin Irvine Ranch: 1915-01-01→1930-12-31 n/a; 1931-01-01→2003-06-30 0700
- ℹ️ UCLA: 1933-03-01→2026-08-23 1600
- ℹ️ Woodland Hills: 1949-07-01→2026-08-21 1600
- ℹ️ Yorba Linda: 1912-10-01→1971-04-06 n/a; 1971-04-07→1982-11-29 1800; 2001-12-01→2007-06-30 1600
- ℹ️ Torrance Airport: 1932-01-01→1945-12-31 n/a; 1946-01-01→1955-09-13 1700; 1955-09-19→1958-12-18 1535; 1958-12-19→1962-01-09 1700; 1962-01-14→2026-08-23 1600
- ℹ️ Long Beach Airport: 1949-01-01→1976-07-15 n/a; 1976-07-16→2026-08-23 2400
- ℹ️ LAX: 1944-08-01→1967-12-31 2400; 1968-01-01→1968-05-28 n/a; 1968-05-29→2026-08-23 2400
- ℹ️ Palmdale Airport: 1934-01-02→2026-08-23 n/a
- ℹ️ El Toro MCAS: 1945-03-01→1998-12-10 n/a
### qflags

- ℹ️ Burbank: 1122 flagged TMAX/TMIN values withheld I=1086, O=4, S=12, Z=20
- ℹ️ Claremont: 303 flagged TMAX/TMIN values withheld G=1, I=280, O=1, S=21
- ℹ️ Corona: 181 flagged TMAX/TMIN values withheld G=1, I=160, S=20
- ℹ️ Culver City: 678 flagged TMAX/TMIN values withheld G=2, I=643, O=20, S=13
- ℹ️ Lake Elsinore: 510 flagged TMAX/TMIN values withheld G=2, I=445, O=13, S=50
- ℹ️ Laguna Beach: 300 flagged TMAX/TMIN values withheld G=1, I=260, O=16, S=23
- ℹ️ Mt. Wilson: 665 flagged TMAX/TMIN values withheld I=654, S=11
- ℹ️ Newport Beach: 544 flagged TMAX/TMIN values withheld G=4, I=526, O=8, S=6
- ℹ️ Palmdale: 408 flagged TMAX/TMIN values withheld G=1, I=375, O=1, S=31
- ℹ️ Pasadena: 152 flagged TMAX/TMIN values withheld G=1, I=139, S=12
- ℹ️ Pomona Fairplex: 1207 flagged TMAX/TMIN values withheld D=62, G=1, I=1099, O=9, S=36
- ℹ️ Riverside: 490 flagged TMAX/TMIN values withheld G=4, I=438, O=4, S=43, Z=1
- ℹ️ Riverside Citrus Station: 22 flagged TMAX/TMIN values withheld I=20, S=2
- ℹ️ San Fernando: 158 flagged TMAX/TMIN values withheld G=4, I=132, S=22
- ℹ️ San Gabriel: 432 flagged TMAX/TMIN values withheld G=2, I=419, O=5, S=6
- ℹ️ Santa Ana: 1647 flagged TMAX/TMIN values withheld G=2, I=1612, O=2, S=31
- ℹ️ Santa Monica Pier: 372 flagged TMAX/TMIN values withheld G=1, I=363, O=6, S=2
- ℹ️ Tustin Irvine Ranch: 685 flagged TMAX/TMIN values withheld G=1, I=665, S=19
- ℹ️ UCLA: 309 flagged TMAX/TMIN values withheld I=296, O=10, S=3
- ℹ️ Woodland Hills: 1413 flagged TMAX/TMIN values withheld I=1394, S=19
- ℹ️ Yorba Linda: 163 flagged TMAX/TMIN values withheld G=1, I=129, O=5, S=28
- ℹ️ Torrance Airport: 228 flagged TMAX/TMIN values withheld G=1, I=178, O=25, S=24
- ℹ️ Long Beach Airport: 1 flagged TMAX/TMIN values withheld S=1
- ℹ️ LAX: 4 flagged TMAX/TMIN values withheld O=4
- ℹ️ Palmdale Airport: 9 flagged TMAX/TMIN values withheld S=8, T=1
- ℹ️ El Toro MCAS: 7 flagged TMAX/TMIN values withheld I=2, O=1, S=4
### whole_degree_f

- ℹ️ ≥99.5% of values round-trip to whole °F everywhere
