import json
import statistics as st

S = "data/analysis/scratch/"
DESERT = (
    "Barstow",
    "Edwards",
    "Blythe",
    "Needles",
    "Palmdale",
    "Lancaster",
    "Victorville",
    "China Lake",
    "Bishop",
    "Twentynine",
    "Palm Springs",
    "Desert Resorts",
    "Imperial",
    "El Centro",
    "Mojave",
    "Daggett",
    "Bicycle",
)
MOUNTAIN = (
    "Blue Canyon",
    "Mt. Shasta",
    "Alturas",
    "Montague",
    "Truckee",
    "Tahoe",
    "Mammoth",
    "Sandberg",
    "Big Bear",
    "Siskiyou",
)
VALLEY = (
    "Sacramento",
    "Stockton",
    "Fresno",
    "Bakersfield",
    "Red Bluff",
    "Beale",
    "Travis",
    "Lemoore",
    "Castle",
    "Merced",
    "Modesto",
    "Madera",
    "Hanford",
    "Visalia",
    "Porterville",
    "Marysville",
    "Oroville",
    "Redding",
    "Vacaville",
    "Mather",
    "Mcclellan",
    "Chico",
)
SOCAL = (
    "Los Angeles",
    "Long Beach",
    "Burbank",
    "Camarillo",
    "Oxnard",
    "Santa Barbara",
    "San Diego",
    "N Is",
    "Miramar",
    "March",
    "Ontario",
    "Van Nuys",
    "Santa Monica",
    "Hawthorne",
    "Torrance",
    "Fullerton",
    "Santa Ana",
    "John Wayne",
    "Chino",
    "Riverside",
    "San Bernardino",
    "Corona",
    "Los Alamitos",
    "Point Mugu",
    "Camp Pendleton",
    "Carlsbad",
    "Oceanside",
    "Gillespie",
    "Brown Field",
    "Montgomery",
    "Ramona",
    "Whiteman",
    "Imperial Beach",
    "Avalon",
    "San Clemente",
    "San Nicolas",
    "Pendleton",
    "Campo",
    "Vandenberg",
    "Lompoc",
    "Santa Maria",
)


def group(name):
    for g, keys in (
        ("Desert", DESERT),
        ("Mountain/N interior", MOUNTAIN),
        ("Central Valley", VALLEY),
        ("SoCal coast & basin", SOCAL),
    ):
        if any(k in name for k in keys):
            return g
    return "Bay Area & Central/North Coast"


def table(rows, keys, label):
    print(f"\n=== {label}: {len(rows)} stations — medians by region (n)")
    groups = {}
    for r in rows:
        groups.setdefault(group(r["short"]), []).append(r)
    print("%-32s %3s " % ("region", "n") + " ".join("%9s" % k for k in keys))
    for g, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        vals = []
        for k in keys:
            v = [r[k] for r in rs if r.get(k) is not None]
            vals.append("%+9.2f" % st.median(v) if v else "        -")
        print("%-32s %3d " % (g, len(rs)) + " ".join(vals))
        print(
            "      "
            + ", ".join(
                r["short"].replace(" Airport", "").replace(" International", "")[:22] for r in rs
            )
        )


fixed = json.load(open(S + "ca_fixed_rows.json"))
table(
    fixed,
    ["peak", "low", "after", "relief", "days", "waves", "ohi", "olo"],
    "1951-80 vs last 30 (fixed windows)",
)
import glob

for f in glob.glob(S + "rows_stations*ca.yaml.json"):
    rows = json.load(open(f))
    table(
        rows,
        ["peak_f", "low_f", "after_low_f", "relief_h", "days", "waves_per_year"],
        "1982-on: first 15 vs last 15 complete summers",
    )
    table(
        rows,
        ["peak_f_trend", "low_f_trend", "after_low_f_trend", "relief_h_trend"],
        "1982-on: Theil-Sen trend per decade",
    )
