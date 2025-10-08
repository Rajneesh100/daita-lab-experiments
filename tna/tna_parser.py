import pandas as pd
import os
from pathlib import Path

def convert_xlsx_to_csv():
    """
    Convert all Excel files (.xlsx) from the xlsheets directory to CSV files 
    and save them in the csvfiles directory with the same filenames.
    """
    
    # Define directories
    xlsheets_dir = Path("xlsheets")
    csvfiles_dir = Path("csvfiles")
    
    # Create csvfiles directory if it doesn't exist
    csvfiles_dir.mkdir(exist_ok=True)
    
    # Check if xlsheets directory exists
    if not xlsheets_dir.exists():
        print(f"❌ Error: Directory '{xlsheets_dir}' does not exist")
        return
    
    # Find all Excel files (.xlsx)
    excel_files = list(xlsheets_dir.glob("*.xlsx"))
    
    if not excel_files:
        print(f"📭 No Excel files (.xlsx) found in '{xlsheets_dir}' directory")
        return
    
    print(f"📊 Found {len(excel_files)} Excel file(s) to convert:")
    
    successful_conversions = 0
    failed_conversions = 0
    
    for excel_file in excel_files:
        try:
            # Get filename without extension for CSV naming
            csv_filename = excel_file.stem + ".csv"
            csv_path = csvfiles_dir / csv_filename
            
            print(f"🔄 Converting: {excel_file.name} -> {csv_filename}")
            
            # Read Excel file
            # Try to read all sheets first
            try:
                # Read all sheets
                excel_data = pd.read_excel(excel_file, sheet_name=None)
                
                if len(excel_data) > 1:
                    print(f"   📄 Multiple sheets found ({len(excel_data)} sheets)")
                    # If multiple sheets, save each as a separate CSV with sheet name
                    for sheet_name, df in excel_data.items():
                        csv_sheet_path = csvfiles_dir / f"{excel_file.stem}_{sheet_name}.csv"
                        df.to_csv(csv_sheet_path, index=False)
                        print(f"   ✅ Sheet '{sheet_name}' saved as: {csv_sheet_path.name}")
                        successful_conversions += 1
                else:
                    # Single sheet - save with original filename
                    df = list(excel_data.values())[0]
                    df.to_csv(csv_path, index=False)
                    print(f"   ✅ Saved as: {csv_filename}")
                    successful_conversions += 1
                    
            except Exception as e:
                print(f"   ❌ Error reading Excel file '{excel_file.name}': {str(e)}")
                failed_conversions += 1
                continue
                
        except Exception as e:
            print(f"❌ Unexpected error converting '{excel_file.name}': {str(e)}")
            failed_conversions += 1
    
    # Summary
    print(f"\n📋 Conversion Summary:")
    print(f"   ✅ Successful: {successful_conversions}")
    print(f"   ❌ Failed: {failed_conversions}")
    print(f"   📁 Output directory: {csvfiles_dir.absolute()}")
    
    if successful_conversions > 0:
        print(f"\n🎉 Successfully converted {successful_conversions} file(s)!")
        print(f"📁 CSV files saved in: {csvfiles_dir.absolute()}")

def list_available_files():
    """
    List all available files in both directories for reference
    """
    print("📋 Directory Contents:")
    
    xlsheets_dir = Path("xlsheets")
    csvfiles_dir = Path("csvfiles")
    
    if xlsheets_dir.exists():
        excel_files = list(xlsheets_dir.glob("*.xlsx"))
        print(f"\n📊 Excel files in '{xlsheets_dir}':")
        if excel_files:
            for file in excel_files:
                print(f"   📄 {file.name}")
        else:
            print("   (No Excel files found)")
    else:
        print(f"\n❌ Directory '{xlsheets_dir}' does not exist")
    
    if csvfiles_dir.exists():
        csv_files = list(csvfiles_dir.glob("*.csv"))
        print(f"\n📄 CSV files in '{csvfiles_dir}':")
        if csv_files:
            for file in csv_files:
                print(f"   📄 {file.name}")
        else:
            print("   (No CSV files found)")
    else:
        print(f"\n❌ Directory '{csvfiles_dir}' does not exist")

if __name__ == "__main__":
    print("🚀 Excel to CSV Converter")
    print("=" * 50)
    
    # List current files
    list_available_files()
    
    print("\n" + "=" * 50)
    
    # Convert files
    convert_xlsx_to_csv()
    
    # List files after conversion
    print("\n" + "=" * 50)
    list_available_files()
