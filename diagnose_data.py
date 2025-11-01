"""
ONA Data Diagnostic Script
Checks your data structure and identifies column names
"""

import pandas as pd
import sys
import json

def diagnose_data(file_path='ona_data_export.csv'):
    """Diagnose the data structure"""
    
    print("=" * 60)
    print("ONA DATA DIAGNOSTIC REPORT")
    print("=" * 60)
    
    try:
        # Load data
        data = pd.read_csv(file_path)
        print(f"\n✅ Successfully loaded data: {len(data)} records")
        
        # Show all column names
        print(f"\n📋 ALL COLUMN NAMES ({len(data.columns)} columns):")
        print("-" * 60)
        for i, col in enumerate(data.columns, 1):
            print(f"{i:2d}. {col}")
        
        # Check for district columns
        print(f"\n📍 DISTRICT-RELATED COLUMNS:")
        print("-" * 60)
        district_cols = [col for col in data.columns if 'district' in col.lower()]
        if district_cols:
            for col in district_cols:
                unique_count = data[col].nunique()
                print(f"✅ {col}: {unique_count} unique values")
                print(f"   Sample values: {data[col].dropna().unique()[:5].tolist()}")
        else:
            print("❌ No columns with 'district' in name found")
            print("   Looking for location-related columns:")
            location_cols = [col for col in data.columns if any(word in col.lower() for word in ['location', 'area', 'region', 'county', 'ward'])]
            if location_cols:
                for col in location_cols:
                    print(f"   - {col}")
        
        # Check for GPS columns
        print(f"\n🌍 GPS-RELATED COLUMNS:")
        print("-" * 60)
        lat_cols = [col for col in data.columns if any(word in col.lower() for word in ['lat', 'latitude'])]
        lon_cols = [col for col in data.columns if any(word in col.lower() for word in ['lon', 'long', 'longitude'])]
        
        if lat_cols:
            for col in lat_cols:
                non_null = data[col].notna().sum()
                print(f"✅ Latitude: {col}")
                print(f"   Non-null values: {non_null}/{len(data)} ({non_null/len(data)*100:.1f}%)")
                if non_null > 0:
                    print(f"   Range: {data[col].min():.6f} to {data[col].max():.6f}")
        else:
            print("❌ No latitude column found")
        
        if lon_cols:
            for col in lon_cols:
                non_null = data[col].notna().sum()
                print(f"✅ Longitude: {col}")
                print(f"   Non-null values: {non_null}/{len(data)} ({non_null/len(data)*100:.1f}%)")
                if non_null > 0:
                    print(f"   Range: {data[col].min():.6f} to {data[col].max():.6f}")
        else:
            print("❌ No longitude column found")
        
        # Check for enumerator columns
        print(f"\n👤 ENUMERATOR-RELATED COLUMNS:")
        print("-" * 60)
        enum_cols = [col for col in data.columns if any(word in col.lower() for word in ['enum', 'interviewer', 'collector', 'worker'])]
        if enum_cols:
            for col in enum_cols:
                unique_count = data[col].nunique()
                print(f"✅ {col}: {unique_count} unique enumerators")
                print(f"   Sample IDs: {data[col].dropna().unique()[:5].tolist()}")
        else:
            print("❌ No enumerator column found")
        
        # Check for time columns
        print(f"\n⏰ TIME-RELATED COLUMNS:")
        print("-" * 60)
        time_cols = [col for col in data.columns if any(word in col.lower() for word in ['time', 'date', 'timestamp'])]
        if time_cols:
            for col in time_cols:
                print(f"✅ {col}")
                print(f"   Sample: {data[col].dropna().iloc[0] if len(data[col].dropna()) > 0 else 'N/A'}")
        else:
            print("❌ No time columns found")
        
        # Generate recommended configuration
        print(f"\n⚙️ RECOMMENDED CONFIGURATION:")
        print("-" * 60)
        
        config = {"column_mapping": {}}
        
        if district_cols:
            config["column_mapping"]["district_column"] = district_cols[0]
        if lat_cols:
            config["column_mapping"]["latitude_column"] = lat_cols[0]
        if lon_cols:
            config["column_mapping"]["longitude_column"] = lon_cols[0]
        if enum_cols:
            config["column_mapping"]["enumerator_column"] = enum_cols[0]
        
        duration_cols = [col for col in data.columns if 'duration' in col.lower()]
        if duration_cols:
            config["column_mapping"]["duration_column"] = duration_cols[0]
        
        print(json.dumps(config, indent=2))
        
        print("\n" + "=" * 60)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"\n❌ ERROR: File '{file_path}' not found!")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

if __name__ == "__main__":
    diagnose_data()
