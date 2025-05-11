import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE  # For handling class imbalance
import matplotlib.pyplot as plt

from sklearn.impute import SimpleImputer
from imblearn.pipeline import Pipeline as ImbPipeline


# at the bottom of feature_analyzer.py

def compute_feature_importances(df: pd.DataFrame, label: str):
    """
    Runs your pipeline on `df`, prints classification report & feature importances,
    and shows the bar-plot.
   """
def determine_win(row)
    home_score, away_score = map(int, row['result'].split('-'))
    if row['is_home'] == 'True':  
        if home_score > away_score:
            return 1  # Win
        elif home_score < away_score:
            return -1  # Loss
        else:
            return 0  # Draw
    else:
        if away_score > home_score:
            return 1  # Win
        elif away_score < home_score:
            return -1  # Loss
        else:
            return 0  # Draw

# Function to extract Real Madrid's goals
def goals(row):
    home_score, away_score = map(int, row['result'].split('-'))
    if row['is_home'] == 'True':  # If Real Madrid is the home team
        return home_score
    else:  # If Real Madrid is the away team
        return away_score

# Apply the function to create a 'win' column
df['win'] = df.apply(determine_win, axis=1)

# Apply the function to create a 'real_madrid_goals' column
df['goals'] = df.apply(goals, axis=1)

df['win_binary'] = (df['win'] == 1).astype(int)


# 3. Clean passes_pct
if 'passes_pct' in df.columns:
    df['passes_pct'] = (
        df['passes_pct']
        .str.rstrip('%')
        .replace('', pd.NA)
        .astype('float64')
    )

# 4. Drop non‐features
drop_cols = ["team","matchday","fixture_id","date","opponent",
             "venue","result","is_home","shots_off_goal","corner_kicks"]
df_model = df.drop(columns=[c for c in drop_cols if c in df.columns])

# 5. Coerce numeric & drop fully empty cols
df_model = df_model.apply(pd.to_numeric, errors='coerce')
df_model = df_model.dropna(axis=1, how='all')  # remove columns like ball_possession with no data

# 6. Split X/y
X = df_model.drop(columns=['win','win_binary'])
y = df_model['win_binary']

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

# 7. Compute dynamic k_neighbors
n_minority    = y_train.value_counts().min()
k_neighbors   = max(1, min(5, n_minority - 1))

# 8. Pipeline: impute → scale → SMOTE → RF
pipeline = ImbPipeline(steps=[
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler',  StandardScaler()),
    ('smote',   SMOTE(random_state=42, k_neighbors=k_neighbors)),
    ('clf',     RandomForestClassifier(random_state=42))
])

# 9. Fit & evaluate
pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

print("k_neighbors:", k_neighbors)
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# 10. Correctly pair feature names & importances
feature_names = X_train.columns
importances    = pipeline.named_steps['clf'].feature_importances_

importance_df = pd.DataFrame({
    'Feature':    feature_names,
    'Importance': importances
}).sort_values(by='Importance', ascending=False)

print("\nFeature Importances:\n", importance_df)

# 11. (Optional) Plot
plt.figure(figsize=(10,6))
plt.barh(importance_df['Feature'], importance_df['Importance'])
plt.gca().invert_yaxis()
plt.xlabel('Importance')
plt.ylabel('Feature')
plt.title('Feature Importance')
plt.tight_layout()
plt.show()
