"""Rattacher explicitement les scores historiques à leur sauvegarde de données."""
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / "Notebooks_Api_Traitement"
for name in ["2_classification_dpe.ipynb", "3_regression_consommation.ipynb"]:
    path = DIRECTORY / name
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        if "df = load_data()" in source:
            if name.startswith("3_"):
                source = '''from src.ml_workflow import load_data, reference_data_path
# Les scores historiques ne doivent pas être attribués au CSV corrigé.
DATA_FOR_EVALUATION = ROOT / "output/cleaned_data.csv" if RUN_TRAINING else reference_data_path()
print("Données utilisées :", DATA_FOR_EVALUATION)
print("Scores historiques avant correction géographique" if not RUN_TRAINING else "Nouvel entraînement explicite")
df = load_data(DATA_FOR_EVALUATION)
'''
            else:
                source = '''from src.ml_workflow import reference_data_path
if RUN_TRAINING:
    raise RuntimeError("Utiliser la comparaison limitée entraînement/validation. Aucun entraînement automatique ici.")
DATA_FOR_EVALUATION = reference_data_path()
print("Référence historique avant corrections géographiques :", DATA_FOR_EVALUATION)
df = load_data(DATA_FOR_EVALUATION)
print("Dimensions :", df.shape)
print(df.etiquette_dpe.value_counts().sort_index())
'''
        if "infos['data_sha256'] != fingerprint()" in source:
            source = source.replace("fingerprint()", "fingerprint(DATA_FOR_EVALUATION)")
        if "DATA_SHA256 = fingerprint()" in source:
            source = source.replace("DATA_SHA256 = fingerprint()", "DATA_SHA256 = fingerprint(DATA_FOR_EVALUATION)")
        if "".join(cell["source"]) != source:
            cell.update(source=source.splitlines(True), outputs=[], execution_count=None)
    if "Les scores historiques sont liés" not in "".join(notebook["cells"][0]["source"]):
        notebook["cells"][0]["source"] += ["\nLes scores historiques sont liés à la sauvegarde antérieure aux corrections géographiques ; ils ne valident pas le nouveau CSV. La comparaison future utilise une validation séparée.\n"]
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
