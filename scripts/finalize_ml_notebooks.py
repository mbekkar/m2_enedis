"""Alignement ciblé des entrées et de la traçabilité des notebooks ML."""
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / "Notebooks_Api_Traitement"


def replace_source(cell, source):
    if "".join(cell["source"]) != source:
        cell["source"] = source.splitlines(True)
        cell["outputs"] = []
        cell["execution_count"] = None


path = DIRECTORY / "3_regression_consommation.ipynb"
notebook = json.loads(path.read_text(encoding="utf-8"))
for cell in notebook["cells"]:
    if cell["cell_type"] != "code":
        continue
    source = "".join(cell["source"])
    if 'df = pd.read_csv("output/cleaned_data.csv"' in source:
        source = "from src.ml_workflow import load_data\n\n# Même lecture et mêmes contrôles que la classification.\ndf = load_data()\n"
    if "mlflow.set_experiment" in source and "COMPARISON_ID" not in source:
        source = source.replace(
            '    mlflow.set_experiment("Hyperparameter Tuning Regression Models")',
            '    from uuid import uuid4\n'
            '    from src.ml_workflow import fingerprint\n'
            '    COMPARISON_ID = uuid4().hex\n'
            '    DATA_SHA256 = fingerprint()\n'
            '    mlflow.set_experiment("Regression consommation finale")')
        source = source.replace(
            '        with mlflow.start_run(run_name=name):',
            '        with mlflow.start_run(run_name=name):\n'
            '            mlflow.set_tags({"comparison_id": COMPARISON_ID,\n'
            '                             "target": target, "data_sha256": DATA_SHA256})')
    if "mlflow.search_runs" in source and "filter_string" not in source:
        source = source.replace(
            'experiment_names=["Hyperparameter Tuning Regression Models"],',
            'experiment_names=["Regression consommation finale"],\n'
            '        filter_string=f"tags.comparison_id = \'{COMPARISON_ID}\'",')
        source = source.replace("].head(7)", "]  # Uniquement les essais de cette exécution et de cette cible.")
    replace_source(cell, source)
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

path = DIRECTORY / "1a_enrichissement_donnees.ipynb"
notebook = json.loads(path.read_text(encoding="utf-8"))
for cell in notebook["cells"]:
    source = "".join(cell["source"])
    if cell["cell_type"] == "code" and source.startswith('print("Dataset nettoyé :"'):
        replace_source(cell, '''# Le périmètre Rhône ne doit pas être remplacé silencieusement par le CSV commun.
required_paths = [
    ROOT / "output/ademe_data_69_cleaned.csv",
    ROOT / "data/communes-france-2025.csv",
    ROOT / "data/climate_zones.csv",
]
missing_paths = [str(p.relative_to(ROOT)) for p in required_paths if not p.is_file()]
if missing_paths:
    raise FileNotFoundError(
        "Enrichissement Rhône non exécutable : fichiers absents : "
        + ", ".join(missing_paths)
        + ". Les modèles courants utilisent output/cleaned_data.csv, issu du notebook 1."
    )
print("Fichiers du périmètre Rhône disponibles.")
''')
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
