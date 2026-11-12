"""Intégrer les corrections géographiques vérifiées dans le notebook commun."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.preparation_geography import backup_file

path = ROOT / "Notebooks_Api_Traitement/1_data_preparation.ipynb"
backup_file(path)
notebook = json.loads(path.read_text(encoding="utf-8"))

changes = {
    20: '''# Préserver la provenance avant la concaténation ; jamais une entrée des modèles.
from src.data_lineage import RAW_FIELDS, LINEAGE_FIELDS
for source, raw in [("existant", df_old), ("neuf", df_new)]:
    raw["_source_dataset"] = source
    raw["_source_row"] = raw.index
df_total = pd.concat([df_old, df_new]).reset_index(drop=True)
''',
    30: '''# Les colonnes de traçabilité seront jointes après le nettoyage.
df = df_total[features].copy()
''',
    73: '''# Les index d'origine sont encore conservés : jointures 1:1 avec les bruts.
df = df.join(df_total[["lat", "lon"]], how="left", validate="one_to_one")
df = df.join(df_total[LINEAGE_FIELDS], how="left", validate="one_to_one")
''',
    88: '''# Corrections de Nouhayla : Lyon et Pierre-Bénite, sur une clé séparée.
# La fonction vérifie l'unicité des communes, l'effectif et l'ordre des logements.
from src.preparation_geography import join_commune_altitudes
df = join_commune_altitudes(df, cities)
''',
    89: '''# Altitudes sans correspondance communale : repli départemental conservé.
missing = df[df["altitude_moyenne"].isna()].drop(columns=["altitude_moyenne"])
''',
    93: '''# Les clés techniques ne sont pas des caractéristiques ML.
df.drop(columns=["code_insee", "code_insee_jointure"], inplace=True)
''',
    96: '''# Sauvegarder le CSV précédent avant de remplacer la version commune.
# Les identifiants et dates sont exportés dans un fichier de traçabilité séparé.
from src.preparation_geography import export_prepared
manifest = export_prepared(df)
print("Version des données :", manifest["version"])
''',
}
for index in (15, 17):
    source = "".join(notebook["cells"][index]["source"])
    if "dtype=" not in source:
        source = "from src.data_lineage import RAW_FIELDS\n" + source.replace(
            "low_memory=False)", 'low_memory=False, dtype={name: "string" for name in RAW_FIELDS})')
    changes[index] = source
for index, source in changes.items():
    cell = notebook["cells"][index]
    if "".join(cell["source"]) != source:
        cell.update(source=source.splitlines(True), outputs=[], execution_count=None)
note = "\n\nCorrections géographiques intégrées de Nouhayla : les codes de Lyon et Pierre-Bénite sont corrigés uniquement pour la jointure d'altitude. Les zones H1/H2/H3 sont conservées. L'export sauvegarde le CSV antérieur et sépare la traçabilité des variables ML. Les modèles existants restent associés au CSV antérieur jusqu'à réentraînement explicite.\n"
if "Corrections géographiques intégrées" not in "".join(notebook["cells"][0]["source"]):
    notebook["cells"][0]["source"] += note.splitlines(True)
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
