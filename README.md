# Demand Forecasting

Application web de prévision de la demande par produit. L’interface permet
d’importer un fichier CSV, d’explorer les données et de générer des prévisions
sur 7, 30 ou 90 jours.

Le projet est composé de deux parties :

- **ASP.NET Core MVC (.NET 8)** : interface utilisateur, import du CSV,
  exploration des données et téléchargement des prévisions.
- **API Flask (Python)** : entraînement des modèles et calcul des prévisions
  hybrides Prophet + Random Forest.

## Fonctionnalités

- Import d’un fichier CSV de ventes.
- Aperçu des données importées avec recherche, tri et pagination.
- Prévision de la demande pour tous les produits ou pour une sélection de
  produits.
- Horizons de prévision de 7, 30 ou 90 jours.
- Tableau de bord avec indicateurs et graphiques.
- Export de toutes les prévisions au format CSV.
- Évaluation comparative des modèles Prophet et hybride.

## Architecture

```text
.
├── DemandForecastingA/
│   ├── DemandForecastingA.sln
│   └── DemandForecastingA/
│       ├── Controllers/
│       ├── Models/
│       ├── Views/
│       └── wwwroot/
└── backend_python/
    ├── api_forecast.py
    ├── evaluate_models.py
    └── data_corrected.csv
```

Le navigateur communique avec l’application ASP.NET Core. Celle-ci envoie les
données au service Python sur `http://127.0.0.1:5000/predict`.

## Prérequis

- Windows 10/11
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Python 3.10 ou version ultérieure
- Une connexion Internet lors de la première installation de Prophet, car
  certaines dépendances peuvent nécessiter des paquets précompilés

## Installation

### 1. Installer les dépendances Python

Depuis le dossier `backend_python`, créer et activer un environnement virtuel,
puis installer les bibliothèques utilisées par l’API :

```powershell
cd backend_python
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install flask flask-cors waitress pandas numpy prophet scikit-learn
```

Si PowerShell bloque l’activation de l’environnement virtuel, exécuter au
besoin :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. Restaurer les dépendances .NET

Depuis la racine du projet :

```powershell
dotnet restore .\DemandForecastingA\DemandForecastingA\DemandForecastingA.csproj
```

## Démarrage

Deux processus doivent être lancés.

### API Python

Dans un premier terminal :

```powershell
cd backend_python
.\.venv\Scripts\Activate.ps1
python .\api_forecast.py
```

L’API écoute sur `http://127.0.0.1:5000`.

### Application ASP.NET Core

Dans un second terminal, depuis la racine du projet :

```powershell
dotnet run --project .\DemandForecastingA\DemandForecastingA
```

Les URLs de développement configurées sont :

- `http://localhost:5268`
- `https://localhost:7180`

Ouvrir ensuite l’une de ces URLs dans un navigateur.

## Format du fichier CSV

Le fichier importé doit contenir au minimum les colonnes suivantes :

| Colonne   | Description                                                       |
| --------- | ----------------------------------------------------------------- |
| `Product` | Nom du produit                                                    |
| `ds`      | Date au format interprétable par pandas, par exemple `2023-01-01` |
| `y`       | Quantité vendue / demande observée                                |

Les colonnes suivantes sont utilisées comme variables explicatives lorsqu’elles
sont présentes :

| Colonne        | Description                            | Valeur par défaut |
| -------------- | -------------------------------------- | ----------------- |
| `On_Promotion` | Indique si le produit est en promotion | `0`               |
| `temperature`  | Température                            | `15`              |
| `price`        | Prix                                   | `3.5`             |

Un exemple de fichier valide est disponible dans
`backend_python/data_corrected.csv`.

## Fonctionnement du modèle

Pour chaque produit :

1. Les variables calendaires (`Year`, `Month`, `Day`, `Weekday`) sont calculées.
2. Prophet estime la tendance temporelle et les effets des régresseurs.
3. Un Random Forest apprend à corriger les résidus de Prophet à partir des
   variables calendaires, de la promotion, de la température et du prix.
4. La prédiction finale correspond à la prédiction Prophet additionnée de la
   correction Random Forest.

L’endpoint `POST /predict` accepte un objet JSON contenant `csv_data`,
`start_date`, `end_date` et, facultativement, `products`.

## Évaluation des modèles

Le script d’évaluation compare Prophet et le modèle hybride sur les données
disponibles :

```powershell
cd backend_python
.\.venv\Scripts\Activate.ps1
python .\evaluate_models.py
```

Les résultats sont écrits dans `evaluation_results.csv`.

## Dépannage

- **Erreur de connexion à l’API** : vérifier que `api_forecast.py` est lancé et
  que le port `5000` est disponible.
- **Erreur de validation CSV** : vérifier la présence de `Product`, `ds` et `y`.
- **Erreur Prophet ou sklearn** : vérifier que l’environnement virtuel est
  activé et que les dépendances Python sont installées.
- **Certificat HTTPS local** : utiliser l’URL HTTP `http://localhost:5268` ou
  faire confiance au certificat de développement .NET.
