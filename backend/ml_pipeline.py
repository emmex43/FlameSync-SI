import pandas as pd
import pickle
from sklearn.ensemble import GradientBoostingRegressor

def build_flamesync_model():
    # 1. Load the raw BASS-II tabular data
    df = pd.read_csv('PSI-25_Experimental table_BASS-II.csv')
    
    # 2. Extract and cast the engineering features to numeric
    df['O2_initial'] = pd.to_numeric(df['Calibrated  initial O2 % by vol '], errors='coerce')
    df['Fan_flow'] = pd.to_numeric(df['Fan display'], errors='coerce')
    df['CO2_final'] = pd.to_numeric(df['Final CO2 % by vol'], errors='coerce')
    
    # Use regex to extract the solid material thickness (e.g., "100 micron PMMA" -> 100.0)
    df['Thickness_um'] = df['Fuel Sample Material'].str.extract(r'(\d+)\s*micron').astype(float)
    
    # 3. Clean and impute missing data
    clean_df = df.dropna(subset=['O2_initial', 'CO2_final']).copy()
    clean_df['Thickness_um'] = clean_df['Thickness_um'].fillna(clean_df['Thickness_um'].median())
    clean_df['Fan_flow'] = clean_df['Fan_flow'].fillna(0)
    
    # 4. Define feature matrix (X) and target array (y)
    X = clean_df[['Thickness_um', 'O2_initial', 'Fan_flow']]
    y = clean_df['CO2_final']
    
    # 5. Train the surrogate model
    model = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
    model.fit(X, y)
    
    # 6. Serialize the trained model for the FastAPI server
    with open('flamesync_model.pkl', 'wb') as f:
        pickle.dump(model, f)
        
    print(f"Model trained on {len(clean_df)} flight runs and serialized to flamesync_model.pkl")

if __name__ == "__main__":
    build_flamesync_model()