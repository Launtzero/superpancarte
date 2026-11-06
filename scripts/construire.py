#!/usr/bin/env python3
"""Écrit les pancartes directement dans index.html (pour les moteurs de recherche et
les navigateurs sans JavaScript) et met à jour sitemap.xml.

À lancer après chaque modification de pancartes.json :  python3 scripts/construire.py
Le script ne touche qu'aux zones entre les marqueurs <!-- mur:debut --> / <!-- mur:fin -->,
<!-- motscles:debut --> / <!-- motscles:fin --> et <!-- donnees:debut --> / <!-- donnees:fin -->.
"""
import html, json, re, collections, datetime, pathlib

RACINE = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://launtzero.github.io/superpancarte/"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

def e(s):
    return html.escape(str(s or ""), quote=True)

def date_fr(d):
    try:
        a, m, j = (int(x) for x in d.split("-"))
        return f"{j} {MOIS[m-1]} {a}"
    except Exception:
        return d or ""

def remplacer(texte, nom, contenu):
    motif = re.compile(rf"(<!-- {nom}:debut -->).*?(<!-- {nom}:fin -->)", re.S)
    if not motif.search(texte):
        raise SystemExit(f"Marqueurs « {nom} » introuvables dans index.html")
    return motif.sub(lambda m: m.group(1) + contenu + m.group(2), texte)

def main():
    data = json.loads((RACINE / "pancartes.json").read_text(encoding="utf-8"))
    ordre = sorted(enumerate(data), key=lambda ip: (ip[1].get("envoi") or "", -ip[0]), reverse=True)
    pancartes = [p for _, p in ordre]

    tuiles = []
    for i, p in enumerate(pancartes):
        dims = f' width="{int(p["w"])}" height="{int(p["h"])}"' if p.get("w") and p.get("h") else ""
        chargement = "" if i < 8 else ' loading="lazy"'
        meta = f'\n        <p class="meta">{e(date_fr(p["date"]))}</p>' if p.get("date") else ""
        tuiles.append(
            f'\n      <button type="button" class="tile" data-i="{i}">'
            f'\n        <img src="images/{e(p["image"])}" alt="{e(p.get("alt") or p.get("texte"))}"{chargement}{dims}>'
            f'\n        <p class="txt">{e(p.get("texte"))}</p>{meta}'
            f'\n      </button>')
    mur = "".join(tuiles) + "\n    "

    compte = collections.Counter(t for p in data for t in (p.get("tags") or []))
    liste = sorted(((t, n) for t, n in compte.items() if n >= 3), key=lambda tn: (-tn[1], tn[0]))
    motscles = "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-tag="{e(t)}">{e(t)}<span>{n}</span></button>'
        for t, n in liste)

    dernier = max((p.get("envoi") or "" for p in data), default="")[:10] or datetime.date.today().isoformat()
    villes = sorted({p["ville"] for p in data if p.get("ville")})
    donnees = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Super Pancarte",
        "url": SITE,
        "inLanguage": "fr",
        "description": "La collection libre et collaborative des pancartes de manif : "
                       f"{len(data)} slogans à chercher par mots-clés pour trouver l'idée de ta prochaine pancarte.",
        "dateModified": dernier,
        "keywords": ", ".join(["pancarte", "slogan", "manifestation", "manif"] + [t for t, _ in liste]),
        "about": [{"@type": "Thing", "name": t} for t, _ in liste],
        "contentLocation": [{"@type": "Place", "name": v} for v in villes],
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(pancartes),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "item": {"@type": "CreativeWork", "name": p.get("texte"), "image": SITE + "images/" + p["image"],
                          **({"locationCreated": {"@type": "Place", "name": p["ville"]}} if p.get("ville") else {}),
                          **({"dateCreated": p["date"]} if p.get("date") else {})}}
                for i, p in enumerate(pancartes)],
        },
    }
    bloc = ('\n<script type="application/ld+json">\n'
            + json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            + "\n</script>\n")

    page = (RACINE / "index.html").read_text(encoding="utf-8")
    page = remplacer(page, "mur", mur)
    page = remplacer(page, "motscles", motscles)
    page = remplacer(page, "donnees", bloc)
    (RACINE / "index.html").write_text(page, encoding="utf-8")

    (RACINE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        f'  <url>\n    <loc>{SITE}</loc>\n    <lastmod>{dernier}</lastmod>\n    <changefreq>hourly</changefreq>\n'
        + "".join(f'    <image:image><image:loc>{e(SITE + "images/" + p["image"])}</image:loc></image:image>\n'
                  for p in pancartes)
        + "  </url>\n</urlset>\n", encoding="utf-8")
    print(f"{len(pancartes)} pancartes et {len(liste)} mots-clés écrits dans index.html ; sitemap.xml à jour.")

if __name__ == "__main__":
    main()
