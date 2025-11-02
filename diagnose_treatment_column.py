"""
Diagnostic Script to Check Treatment Column Values
Run this to see what's actually in your data
"""

import pandas as pd
import sys

def diagnose_treatment_data(csv_file='ona_data_export.csv'):
    """Check what treatment/beneficiary values are in the data"""
    
    print("=" * 80)
    print("TREATMENT COLUMN DIAGNOSTIC")
    print("=" * 80)
    
    try:
        # Load data
        df = pd.read_csv(csv_file)
        print(f"\n✅ Loaded {len(df)} records from {csv_file}")
        
        # Find treatment-related columns
        treatment_keywords = ['treatment', 'beneficiary', 'group', 'status', 'type']
        treatment_cols = [col for col in df.columns 
                         if any(keyword in col.lower() for keyword in treatment_keywords)]
        
        print(f"\n📋 TREATMENT-RELATED COLUMNS FOUND:")
        print("-" * 80)
        
        if not treatment_cols:
            print("❌ No treatment-related columns found!")
            print("\nSearching ALL column names:")
            for i, col in enumerate(df.columns, 1):
                print(f"{i:3d}. {col}")
            return
        
        # Analyze each treatment column
        for col in treatment_cols:
            print(f"\n🔍 Column: {col}")
            print("-" * 80)
            
            # Get unique values
            unique_vals = df[col].unique()
            print(f"Unique values ({len(unique_vals)}): {unique_vals}")
            
            # Value counts
            print(f"\nValue distribution:")
            value_counts = df[col].value_counts()
            for val, count in value_counts.items():
                pct = (count / len(df) * 100)
                print(f"  {val!r:30s} : {count:4d} ({pct:5.1f}%)")
            
            # Check data type
            print(f"\nData type: {df[col].dtype}")
            
            # Show sample values
            print(f"\nSample values (first 10 non-null):")
            sample = df[col].dropna().head(10)
            for idx, val in enumerate(sample, 1):
                print(f"  {idx:2d}. {val!r} (type: {type(val).__name__})")
        
        # Find district column
        print("\n" + "=" * 80)
        print("DISTRICT COLUMN CHECK")
        print("=" * 80)
        
        district_cols = [col for col in df.columns if 'district' in col.lower()]
        if district_cols:
            for col in district_cols:
                print(f"\n📍 District column: {col}")
                districts = df[col].value_counts()
                print(f"Districts found ({len(districts)}):")
                for dist, count in districts.items():
                    print(f"  {dist:20s} : {count:4d}")
        else:
            print("❌ No district column found")
        
        # Create cross-tabulation if we have both
        if treatment_cols and district_cols:
            print("\n" + "=" * 80)
            print("CROSS-TABULATION: DISTRICTS vs TREATMENT")
            print("=" * 80)
            
            treatment_col = treatment_cols[0]
            district_col = district_cols[0]
            
            crosstab = pd.crosstab(
                df[district_col], 
                df[treatment_col], 
                margins=True
            )
            
            print(f"\n{crosstab}")
            
            print("\n✅ This is the data that SHOULD appear in your table!")
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
    except FileNotFoundError:
        print(f"\n❌ ERROR: File '{csv_file}' not found!")
        print("Make sure the file is in the same directory as this script.")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if a file was provided as argument
    if len(sys.argv) > 1:
        diagnose_treatment_data(sys.argv[1])
    else:
        diagnose_treatment_data()
