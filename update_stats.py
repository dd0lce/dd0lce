"""Rellena las stats y la gráfica de contribuciones de dd0lce.svg con datos de la API de GitHub."""
import datetime as dt
import json
import os
import re
import urllib.request

USER = os.environ["USER_LOGIN"]
TOKEN = os.environ["GH_TOKEN"]
SVG = "dd0lce.svg"
WIDTH = 58  # ancho en caracteres de la columna derecha
CELL = {"NONE": " ·", "FIRST_QUARTILE": "░░", "SECOND_QUARTILE": "▒▒",
        "THIRD_QUARTILE": "▓▓", "FOURTH_QUARTILE": "██"}


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": query, "variables": {"l": USER}}).encode(),
        {"Authorization": f"bearer {TOKEN}"},
    )
    res = json.load(urllib.request.urlopen(req))
    if "errors" in res:
        raise SystemExit(res["errors"])
    return res["data"]["user"]


# ponytail: solo los primeros 100 repos cuentan para las estrellas; paginar si pasas de 100
u = gql("""query($l:String!){user(login:$l){
  createdAt followers{totalCount}
  repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
  repositories(ownerAffiliations:OWNER,first:100){totalCount nodes{stargazerCount}}
  contributionsCollection{contributionCalendar{totalContributions
    weeks{contributionDays{weekday contributionLevel}}}}}}""")

# La API solo da contribuciones por ventanas de 1 año: una consulta con un alias por año.
now = dt.datetime.now(dt.timezone.utc)
years = range(int(u["createdAt"][:4]), now.year + 1)
to = lambda y: now.strftime("%Y-%m-%dT%H:%M:%SZ") if y == now.year else f"{y}-12-31T23:59:59Z"
per_year = gql("query($l:String!){user(login:$l){" + "".join(
    f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{to(y)}"){{contributionCalendar{{totalContributions}}}}'
    for y in years) + "}}")
contribs = sum(c["contributionCalendar"]["totalContributions"] for c in per_year.values())

stats = {
    "repos": ("Repos", f"{u['repositories']['totalCount']} {{Contributed: {u['repositoriesContributedTo']['totalCount']}}}"),
    "stars": ("Stars", str(sum(r["stargazerCount"] for r in u["repositories"]["nodes"]))),
    "commits": ("Contributions", f"{contribs:,}"),
    "followers": ("Followers", str(u["followers"]["totalCount"])),
}

svg = open(SVG, encoding="utf-8").read()
put = lambda s, id, text: re.sub(rf'(id="{id}"[^>]*>)[^<]*', lambda m: m.group(1) + text, s)
for id, (label, value) in stats.items():
    svg = put(svg, id, value.replace("&", "&amp;"))
    svg = put(svg, id + "_dots", "." * (WIDTH - len(label) - len(value) - 3))

cal = u["contributionsCollection"]["contributionCalendar"]
rows = [["  "] * len(cal["weeks"]) for _ in range(7)]
for w, week in enumerate(cal["weeks"]):
    for day in week["contributionDays"]:
        rows[day["weekday"]][w] = CELL[day["contributionLevel"]]
tspans = "".join(f'<tspan x="505" dy="{0 if i == 0 else 16}">{"".join(r)}</tspan>' for i, r in enumerate(rows))
svg = re.sub(r'(<text id="heat"[^>]*>).*?(</text>)', lambda m: m.group(1) + tspans + m.group(2), svg, flags=re.S)
svg = put(svg, "total", f"{cal['totalContributions']:,} contributions in the last year")

open(SVG, "w", encoding="utf-8").write(svg)
print(stats, cal["totalContributions"])
