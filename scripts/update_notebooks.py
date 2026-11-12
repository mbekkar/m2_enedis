"""Migration ciblée et idempotente des notebooks existants (stdlib uniquement)."""
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / "Notebooks_Api_Traitement"
BOOTSTRAP = '''from pathlib import Path
import os
import sys

ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents]
             if (p / "pyproject.toml").exists() and (p / "MLmodels").is_dir()), None)
if ROOT is None:
    raise RuntimeError("Ouvrez le notebook depuis le dépôt App_Enedis.")
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print("Racine du projet :", ROOT)
'''


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.splitlines(True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def change(notebook, index, source):
    notebook["cells"][index] = cell("code", source)


def save(path, nb):
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def migrate():
    path = DIRECTORY / "1_data_preparation.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if not any("REFERENCE_YEAR" in "".join(c["source"]) for c in nb["cells"]):
        change(nb, 3, BOOTSTRAP + "\nREFERENCE_YEAR = 2026  # Année utilisée par le CSV et le modèle conservés.\n" + "".join(nb["cells"][3]["source"]))
        for i in (19, 38):
            change(nb, i, "".join(nb["cells"][i]["source"]).replace("dt.datetime.now().year", "REFERENCE_YEAR"))
        change(nb, 82, '''# Réutiliser le fichier local ; aucun téléchargement automatique.
chemin = Path("data/communes-france-2025.csv")
if not chemin.is_file():
    raise FileNotFoundError(f"Table des communes absente : {chemin}")
print("Table locale :", chemin)
''')
        for i in range(98, len(nb["cells"])):
            c = nb["cells"][i]
            if c["cell_type"] == "code":
                change(nb, i, "# Agrégation API facultative, désactivée par défaut.\nif EXTRACTION:\n" + "".join("    " + line + "\n" for line in "".join(c["source"]).splitlines()))
        save(path, nb)

    path = DIRECTORY / "1a_enrichissement_donnees.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if "os.chdir(r" in "".join(nb["cells"][0]["source"]):
        change(nb, 0, BOOTSTRAP + "\nimport pandas as pd\nimport numpy as np\n")
        nb["cells"].insert(0, cell("markdown", "# Enrichissement historique du Rhône\n\nCe travail de Nouhayla porte sur 13 481 logements du Rhône. Il nécessite les fichiers `output/ademe_data_69_cleaned.csv` et `data/climate_zones.csv`, absents du poste audité. Il ne constitue pas l'entrée commune des modèles actuels. Le notebook 1 fournit déjà altitude et zones H1/H2/H3 dans `output/cleaned_data.csv`. Ne pas remplacer ces zones par H1c/H2d sans réentraîner les modèles. Les corrections des codes INSEE de Lyon et Pierre-Bénite méritent une intégration ultérieure, avec nouvelle version du CSV et des modèles.\n"))
        save(path, nb)

    path = DIRECTORY / "3_regression_consommation.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if not any("RUN_TRAINING" in "".join(c["source"]) for c in nb["cells"]):
        change(nb, 2, BOOTSTRAP + "\n" + "".join(nb["cells"][2]["source"]))
        change(nb, 3, "IGNORE = True  # La recherche longue est facultative.\nRUN_TRAINING = False  # Réutiliser le modèle sauvegardé par défaut.\n")
        change(nb, 8, "".join(nb["cells"][8]["source"]).replace("# Specifying quantitatives and qualitatives features (same as classification but with cout_total_5_usages as target).", "# Caractéristiques du logement ; cible = consommation finale en kWh/an.\n# Coût, étiquette DPE et consommations détaillées exclus des entrées."))
        for i in (23, 24):
            change(nb, i, "if not IGNORE:\n" + "".join("    " + line + "\n" for line in "".join(nb["cells"][i]["source"]).splitlines()))
        change(nb, 21, "".join(nb["cells"][21]["source"]).replace("n=30000", "n=min(30000, len(Xtrain))"))
        source = "".join(nb["cells"][30]["source"])
        source = source.replace("pipeline.fit(Xtrain, ytrain)\npredictions = pipeline.predict(Xtest)", "if RUN_TRAINING:\n    pipeline.fit(Xtrain, ytrain)\nelse:\n    pipeline = joblib.load(ROOT / 'MLmodels/pipeline_random_forest_consommation.pkl')\npredictions = pipeline.predict(Xtest)")
        change(nb, 30, source)
        for i in (36, 37):
            change(nb, i, "if RUN_TRAINING:\n" + "".join("    " + line + "\n" for line in "".join(nb["cells"][i]["source"]).splitlines()))
        nb["cells"].insert(0, cell("markdown", "# Régression de consommation finale\n\nSource commune : `output/cleaned_data.csv`, issue du notebook 1. Par défaut, le pipeline local est rechargé : ni recherche ni entraînement. Activer `IGNORE = False` pour la comparaison longue, ou `RUN_TRAINING = True` pour réentraîner et sauvegarder. Scores revérifiés le 29 octobre 2026 sans entraînement. Le test a servi à comparer les modèles : ces scores ne sont pas une validation externe. L'échantillon contient beaucoup de logements neufs ; il ne représente pas à lui seul le parc français.\n"))
        save(path, nb)

    path = DIRECTORY / "2_classification_dpe.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if not any("pipeline_classification_common" in "".join(c["source"]) for c in nb["cells"]):
        # Conserver intégralement les expériences de groupe dans une archive lisible.
        archive = DIRECTORY / "archives"
        archive.mkdir(exist_ok=True)
        archived = archive / "2_classification_dpe_rhone_historique.ipynb"
        if not archived.exists():
            archived.write_bytes(path.read_bytes())
        nb["cells"] = [
            cell("markdown", "# Classification DPE — source commune\n\nLe travail historique sur le Rhône est conservé intégralement dans `archives/2_classification_dpe_rhone_historique.ipynb`. Ses scores ne sont pas ceux du CSV commun. Ce notebook utilise les mêmes sept caractéristiques de logement que la régression, sans coût ni consommation. Un seul Random Forest à profondeur limitée est évalué, sans recherche longue. Les performances de F et G doivent être lues séparément.\n"),
            cell("code", BOOTSTRAP + "\nimport json\nimport joblib\nimport numpy as np\nfrom src.ml_workflow import (load_data, split_classification, train_classification,\n                             CLASS_MODEL, CLASS_REPORT, fingerprint)\nRUN_TRAINING = False  # Activer uniquement pour refaire l'entraînement.\n"),
            cell("code", "df = load_data()\nprint('Dimensions :', df.shape)\nprint('Départements :', df.code_departement_ban.nunique())\nprint(df.etiquette_dpe.value_counts().sort_index())\n"),
            cell("code", "if RUN_TRAINING:\n    pipeline, infos = train_classification(df)\nelse:\n    pipeline = joblib.load(CLASS_MODEL)  # pipeline_classification_common.pkl\n    infos = json.loads(CLASS_REPORT.read_text(encoding='utf-8'))\nif infos['data_sha256'] != fingerprint():\n    raise ValueError('Le CSV a changé : réentraîner avant de publier des résultats.')\nX_train, X_test, y_train, y_test = split_classification(df)\ny_pred_rf = pipeline.predict(X_test)\n"),
            cell("code", "from sklearn.metrics import accuracy_score, f1_score, classification_report\nprint('Accuracy :', accuracy_score(y_test, y_pred_rf))\nprint('F1 macro :', f1_score(y_test, y_pred_rf, average='macro'))\nprint(classification_report(y_test, y_pred_rf, digits=3, zero_division=0))\nnp.testing.assert_allclose(accuracy_score(y_test, y_pred_rf), infos['accuracy'])\nnp.testing.assert_allclose(f1_score(y_test, y_pred_rf, average='macro'), infos['f1_macro'])\n"),
            cell("code", "from sklearn.metrics import ConfusionMatrixDisplay\nimport matplotlib.pyplot as plt\nConfusionMatrixDisplay.from_predictions(y_test, y_pred_rf, labels=list('ABCDEFG'))\nplt.title('DPE — source commune, test stratifié de 30 %')\nplt.show()\n"),
            cell("code", "modele_recharge = joblib.load(CLASS_MODEL)\nnp.testing.assert_array_equal(pipeline.predict(X_test.head(20)), modele_recharge.predict(X_test.head(20)))\nprint('Prédictions identiques après rechargement.')\n"),
            cell("markdown", "Les paramètres sont fixés avant l'évaluation ; aucun réglage n'est sélectionné sur le test. L'évaluation reste interne au CSV, sans validation sur une autre période ou un autre territoire. Le DPE prédit est une estimation statistique, pas un diagnostic réglementaire. Les modèles historiques du Rhône restent dans MLmodels sous leurs noms initiaux.\n"),
        ]
        save(path, nb)


if __name__ == "__main__":
    migrate()
