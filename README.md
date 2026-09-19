# Dice Throne Helper

Calculateur exact d'aide à la relance pour Dice Throne. Il explore l'arbre complet
des résultats et utilise une programmation dynamique : aucune simulation aléatoire
n'intervient dans les probabilités.

La première version prend en charge cinq dés identiques et relançables, deux
relances, les combinaisons minimales de symboles, les Petites Suites et les Grandes
Suites. Les personnages à six dés, à dé verrouillé ou à dés empruntés sont hors
périmètre.

## Utilisation

Python 3.11 ou supérieur suffit ; le projet n'a aucune dépendance d'exécution.
Pour générer puis ouvrir le rapport d'un personnage :

```bash
./generate-report.sh chasseresse
```

Sans argument, le script affiche les personnages disponibles : utilisez les
flèches ↑/↓ puis Entrée pour sélectionner celui à générer.

```bash
./generate-report.sh
```

Le fichier d'analyse n'est recalculé que s'il manque ou si le JSON du personnage
est plus récent. Le rapport HTML est toujours régénéré puis ouvert avec `open`.
Les capacités dont le nom se termine par `*` sont ignorées par défaut dans le
rapport ; cochez « Inclure les capacités améliorées » pour les réintégrer dans
les classements et les probabilités d'issues accidentelles.

### Commandes manuelles

Pour installer la commande dans un environnement virtuel :

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/dicethrone-helper analyze characters/chasseresse.json \
  --output build/chasseresse.analysis.json
.venv/bin/dicethrone-helper report build/chasseresse.analysis.json \
  --output build/chasseresse.report.html
```

Les deux commandes sont volontairement séparées. L'artefact d'analyse est un JSON
versionné, déterministe et partageable. Plusieurs présentations peuvent donc être
générées sans refaire les calculs probabilistes.

Sans installation, les mêmes commandes sont accessibles ainsi :

```bash
PYTHONPATH=src python3 -m dicethrone_helper analyze \
  characters/chasseresse.json --output build/chasseresse.analysis.json
PYTHONPATH=src python3 -m dicethrone_helper report \
  build/chasseresse.analysis.json --output build/chasseresse.report.html
```

## Ajouter un personnage

Copier `characters/chasseresse.json`, puis modifier :

- `name` : nom affiché ;
- `symbols` : symboles des faces 1 à 6, dans l'ordre ;
- `abilities` : chaque capacité définit exactement `symbols` ou `straight`.

Une combinaison symbolique exprime des minima. `AAA` accepte donc trois, quatre ou
cinq A. Les seules valeurs de `straight` supportées sont `small` et `large`.

Exemple minimal :

```json
{
  "schema_version": 1,
  "name": "Exemple",
  "symbols": "AAABBC",
  "abilities": [
    { "name": "Attaque", "symbols": "AABBC" },
    { "name": "Petite Suite", "straight": "small" }
  ]
}
```

## Vérification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Les tests couvrent les règles, la dépendance à la distribution propre au
personnage, des probabilités fermées calculées indépendamment, le format d'analyse,
le rapport autonome et le parcours complet de la CLI.
