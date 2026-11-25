import json
import time
import urllib.error
import urllib.parse
import urllib.request

DEPARTEMENTS = ["16"]

CODES_NAF = [
    "62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z",
    "58.29C", "63.11Z", "63.12Z",
    "61.10Z", "61.20Z", "61.90Z",
    "47.41Z", "47.42Z", "46.51Z", "46.52Z",
    "95.11Z", "95.12Z", "33.13Z", "33.14Z",
    "26.11Z", "26.12Z", "26.20Z", "26.30Z",
    "27.12Z", "43.21A", "43.21B", "80.20Z",
]

# Ajouter Des Entreprises
NOMS_A_AJOUTER = [
    "Ordimarques", "STG Micro Informatique",
]

FICHIER_SORTIE = "entreprises.geojson"

EXCLURE_ENTREPRENEURS_INDIVIDUELS = True
EFFECTIF_MINIMUM = "02"
GARDER_EFFECTIF_INCONNU = False

API = "https://recherche-entreprises.api.gouv.fr/search"
ORDRE_EFFECTIF = ["00", "01", "02", "03", "11", "12", "21", "22",
                  "31", "32", "41", "42", "51", "52", "53"]
SECTEURS = {
    "62": "Informatique",
    "58": "Édition de logiciels",
    "63": "Hébergement et données",
    "61": "Télécoms et réseaux",
    "47": "Commerce informatique et télécoms",
    "46": "Commerce informatique et télécoms",
    "95": "Maintenance informatique",
    "33": "Maintenance informatique",
    "26": "Électronique",
    "27": "Électricité et installations",
    "43": "Électricité et installations",
    "80": "Sécurité",
}


def appeler_api(params):
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for essai in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as reponse:
                return json.load(reponse)
        except urllib.error.HTTPError as erreur:
            if erreur.code == 429:
                time.sleep(2 * (essai + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2)
    raise RuntimeError("API injoignable")


def toutes_les_pages(params):
    page = 1
    while True:
        donnees = appeler_api({**params, "per_page": 25, "page": page})
        yield from donnees.get("results", [])
        total_pages = donnees.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.2)


def effectif_ok(tranche):
    if EFFECTIF_MINIMUM is None:
        return True
    if not tranche:
        return GARDER_EFFECTIF_INCONNU
    if tranche not in ORDRE_EFFECTIF:
        return False
    return ORDRE_EFFECTIF.index(tranche) >= ORDRE_EFFECTIF.index(EFFECTIF_MINIMUM)


def vers_features(entreprise, departement, filtrer=True):
    nature = str(entreprise.get("nature_juridique") or "")
    if filtrer and EXCLURE_ENTREPRENEURS_INDIVIDUELS and nature.startswith("1"):
        return []

    etablissements = entreprise.get("matching_etablissements") or [entreprise.get("siege") or {}]
    resultat = []
    for etab in etablissements:
        if etab.get("etat_administratif") not in (None, "A"):
            continue
        code_postal = str(etab.get("code_postal") or "")
        if len(departement) == 2 and departement.isdigit() and code_postal \
                and not code_postal.startswith(departement):
            continue
        tranche = etab.get("tranche_effectif_salarie") or entreprise.get("tranche_effectif_salarie")
        if filtrer and not effectif_ok(tranche):
            continue
        lat, lon = etab.get("latitude"), etab.get("longitude")
        if not lat or not lon:
            continue
        naf = etab.get("activite_principale") or entreprise.get("activite_principale") or ""
        if filtrer and naf not in CODES_NAF:
            continue
        secteur = SECTEURS.get(naf[:2], "Autre")
        resultat.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "name": entreprise.get("nom_complet") or "Entreprise",
                "description": f"**{secteur}** (NAF {naf})\n\n{etab.get('adresse') or ''}",
                "secteur": secteur,
                "naf": naf,
                "siret": etab.get("siret") or "",
                "commune": etab.get("libelle_commune") or "",
            },
        })
    return resultat


def main():
    features, deja_vus = [], set()

    def ajouter(liste):
        for feature in liste:
            siret = feature["properties"]["siret"]
            if siret not in deja_vus:
                deja_vus.add(siret)
                features.append(feature)

    for dep in DEPARTEMENTS:
        params = {
            "departement": dep,
            "activite_principale": ",".join(CODES_NAF),
            "etat_administratif": "A",
        }
        for entreprise in toutes_les_pages(params):
            ajouter(vers_features(entreprise, dep))
        print(f"Département {dep} : {len(features)} entreprises gardées")

        for nom in NOMS_A_AJOUTER:
            params = {"q": nom, "departement": dep, "etat_administratif": "A"}
            trouvees = 0
            for entreprise in toutes_les_pages(params):
                nouvelles = vers_features(entreprise, dep, filtrer=False)
                trouvees += len(nouvelles)
                ajouter(nouvelles)
            print(f"  Ajout manuel « {nom} » : {trouvees} établissement(s) trouvé(s)")

    if not features:
        raise RuntimeError("Aucune entreprise trouvée : fichier non modifié")

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features},
                  f, ensure_ascii=False, indent=1)
    print(f"Terminé : {len(features)} entreprises écrites dans {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()
