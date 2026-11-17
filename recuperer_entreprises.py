#!/usr/bin/env python3
"""
Récupère les entreprises d'un ou plusieurs départements via l'API
« Recherche d'entreprises » (api.gouv.fr, sans clé) et produit un fichier
GeoJSON à charger dans uMap.

Utilisation :  python3 recuperer_entreprises.py
Aucune installation : seulement la bibliothèque standard de Python 3.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------- À MODIFIER SELON TES BESOINS ----------
DEPARTEMENTS = ["16"]  # 16 = Charente (Angoulême). Ajoute "17", "24", "79", "86"...
CODES_NAF = [
    "62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z",  # informatique
    "61.10Z", "61.20Z", "61.90Z",                      # télécoms / réseaux
    "63.11Z",                                          # hébergement, données
    "43.21A", "43.21B",                                # installations électriques
    "95.11Z", "95.12Z",                                # maintenance informatique
]
FICHIER_SORTIE = "entreprises.geojson"

# Retire les entrepreneurs individuels (auto-entrepreneurs, micro-entreprises...)
EXCLURE_ENTREPRENEURS_INDIVIDUELS = True
# Retire aussi les unités qui n'ont jamais déclaré de salarié (code « NN » de l'Insee).
# Mets False si tu trouves qu'il manque trop d'entreprises sur la carte.
EXCLURE_SANS_SALARIE = True
# --------------------------------------------------

API = "https://recherche-entreprises.api.gouv.fr/search"
SECTEURS = {
    "62": "Informatique",
    "61": "Télécoms et réseaux",
    "63": "Hébergement et données",
    "43": "Électricité et installations",
    "95": "Maintenance informatique",
}


def appeler_api(departement, page):
    """Interroge l'API pour une page de résultats (avec quelques essais)."""
    params = {
        "departement": departement,
        "activite_principale": ",".join(CODES_NAF),
        "etat_administratif": "A",  # entreprises en activité uniquement
        "per_page": 25,
        "page": page,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for essai in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as reponse:
                return json.load(reponse)
        except urllib.error.HTTPError as erreur:
            if erreur.code == 429:  # trop de requêtes : on attend
                time.sleep(2 * (essai + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2)
    raise RuntimeError(f"API injoignable (département {departement}, page {page})")


def vers_feature(entreprise):
    """Transforme un résultat de l'API en point GeoJSON (ou None sans GPS)."""
    # Nature juridique : tous les codes qui commencent par « 1 » sont des personnes
    # physiques (1000 = entrepreneur individuel, dont les auto-entrepreneurs).
    nature = str(entreprise.get("nature_juridique") or "")
    if EXCLURE_ENTREPRENEURS_INDIVIDUELS and nature.startswith("1"):
        return None
    if EXCLURE_SANS_SALARIE and entreprise.get("tranche_effectif_salarie") == "NN":
        return None

    siege = entreprise.get("siege") or {}
    lat, lon = siege.get("latitude"), siege.get("longitude")
    if not lat or not lon:
        return None
    naf = entreprise.get("activite_principale") or ""
    secteur = SECTEURS.get(naf[:2], "Autre")
    nom = entreprise.get("nom_complet") or "Entreprise"
    adresse = siege.get("adresse") or ""
    siret = siege.get("siret") or ""
    description = (
        f"**{secteur}** (NAF {naf})\n\n{adresse}\n\n"
        f"[Fiche officielle](https://annuaire-entreprises.data.gouv.fr/"
        f"entreprise/{entreprise.get('siren', '')})"
    )
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
        "properties": {
            "name": nom,            # uMap affiche « name » comme titre
            "description": description,  # et « description » dans la popup
            "secteur": secteur,
            "naf": naf,
            "siret": siret,
            "commune": siege.get("libelle_commune") or "",
        },
    }


def main():
    features, deja_vus = [], set()
    for dep in DEPARTEMENTS:
        page = 1
        while True:
            donnees = appeler_api(dep, page)
            for entreprise in donnees.get("results", []):
                feature = vers_feature(entreprise)
                siret = feature and feature["properties"]["siret"]
                if feature and siret not in deja_vus:
                    deja_vus.add(siret)
                    features.append(feature)
            total_pages = donnees.get("total_pages", 1)
            print(f"Département {dep} : page {page}/{total_pages} "
                  f"({len(features)} entreprises gardées)")
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.2)  # l'API limite à ~7 requêtes par seconde

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features},
                  f, ensure_ascii=False, indent=1)
    print(f"Terminé : {len(features)} entreprises écrites dans {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()
