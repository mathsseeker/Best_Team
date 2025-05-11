import pandas as pd
import warnings
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
import matplotlib.pyplot as plt
from get_team_stats import get_team_match_stats_for_seasons


def select_and_preprocess(df: pd.DataFrame, team_name: str) -> pd.DataFrame:
    """
    Selects only relevant features, handles percentages, imputes missing,
    and creates target labels with robust error handling.
    Always returns a DataFrame suitable for modeling.
    """
    # Work on a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Create 'is_home'
    df['is_home'] = df.get('home_team') == team_name

    # Compute win/draw/loss
    def _win(row):
        try:
            h = int(row.get('home_goals', 0) or 0)
            a = int(row.get('away_goals', 0) or 0)
            if row.get('is_home'):
                return 1 if h > a else -1 if h < a else 0
            else:
                return 1 if a > h else -1 if a < h else 0
        except Exception:
            return 0

    df['win'] = df.apply(_win, axis=1)
    df['win_binary'] = (df['win'] == 1).astype(int)

    # Define features
    features = [
        'shots_on_goal', 'shots_off_goal', 'total_shots', 'blocked_shots',
        'shots_insidebox', 'shots_outsidebox', 'fouls', 'corner_kicks',
        'offsides', 'ball_possession', 'yellow_cards', 'red_cards',
        'goalkeeper_saves', 'total_passes', 'passes_accurate', 'passes_pct',
        'expected_goals'
    ]
    # Filter columns if missing
    features = [c for c in features if c in df.columns]

    # Subset
    df_model = df[features + ['is_home', 'win', 'win_binary']]

    # Convert percentage columns safely
    for pct in ['ball_possession', 'passes_pct']:
        if pct in df_model.columns:
            try:
                df_model.loc[:, pct] = (
                    pd.to_numeric(
                        df_model[pct].astype(str).str.rstrip('%'),
                        errors='coerce'
                    )
                )
            except Exception:
                warnings.warn(f"Failed to convert percentage column {pct}")
                df_model.loc[:, pct] = pd.NA

    # Identify numeric cols for imputation
    num_cols = df_model.select_dtypes(include='number').columns.tolist()
    # Exclude columns with all NaN
    valid_num_cols = [c for c in num_cols if df_model[c].notna().any()]

    # Impute remaining numeric columns
    if valid_num_cols:
        imputer = SimpleImputer(strategy='mean')
        try:
            df_model.loc[:, valid_num_cols] = imputer.fit_transform(df_model[valid_num_cols])
        except Exception as e:
            warnings.warn(f"Imputation failed: {e}")
    else:
        warnings.warn("No numeric columns available for imputation.")

    # Final fill for any residual missing
    df_model = df_model.fillna(0)

    return df_model


def compute_feature_importances(df: pd.DataFrame):
    """Fits RF pipeline and reports importances with error handling."""
    try:
        X = df.drop(columns=['win', 'win_binary'])
        y = df['win_binary']
    except KeyError:
        raise ValueError("DataFrame must contain 'win' and 'win_binary' columns.")

    # Split
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
    except Exception as e:
        raise ValueError(f"Train/test split failed: {e}")

    # Dynamic k_neighbors
    min_count = y_train.value_counts().min()
    k_n = max(1, min(5, min_count - 1))

    pipeline = ImbPipeline([
        ('scale', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=k_n)),
        ('clf', RandomForestClassifier(random_state=42))
    ])

    # Fit & predict
    try:
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
    except Exception as e:
        raise RuntimeError(f"Model training/prediction failed: {e}")

    print("k_neighbors:", k_n)
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    # Feature importances
    try:
        importances = pipeline.named_steps['clf'].feature_importances_
        imp_df = pd.DataFrame({
            'Feature': X.columns,
            'Importance': importances
        }).sort_values('Importance', ascending=False)
        print("\nFeature Importances:\n", imp_df)

        plt.figure(figsize=(10,6))
        plt.barh(imp_df['Feature'], imp_df['Importance'])
        plt.gca().invert_yaxis()
        plt.xlabel('Importance')
        plt.title('Feature Importances')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        warnings.warn(f"Failed to compute or plot feature importances: {e}")


if __name__ == '__main__':
    team_id = '9'
    team_name = 'Spain'
    seasons = ['2022', '2023']
    league_ids = [960, 10, 1, 5]

    raw_df = get_team_match_stats_for_seasons(team_id, seasons, league_ids)
    df_proc = select_and_preprocess(raw_df, team_name)
    compute_feature_importances(df_proc)
