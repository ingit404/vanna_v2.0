import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from src.vanna_sql import MyVanna
from src.config import load_config

load_dotenv()
print(".env file loaded successfully! ✅")

config = load_config()
print("Configuration loaded! ✅")

vn = MyVanna(config=config)
creds = Credentials.from_service_account_file(
    r"C:\Users\Ingit.Paul.in\Downloads\vana-doc-train-8f85103e3c33.json",
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

client = gspread.authorize(creds)
Workbook_name = client.open("Training_Vanna")  

print("Connected to Google Sheets! ✅")


def mark_processed(sheet, row_index, col_index):
    timestamp = datetime.now().isoformat()
    sheet.update_cell(row_index, col_index, timestamp)
    print(f"✔ Marked row {row_index} processed at {timestamp}")



def train_q_sql():
    sheet = Workbook_name.worksheet("Q-SQL")
    rows = sheet.get_all_records()

    print("\n Training Q-SQL Rows")

    for i, row in enumerate(rows, start=2):  
        if not row["Processed_at"] and row["Question"] and row["SQL"]:
            print(f"row {i}: {row['Question']}")

            vn.train(question=row["Question"], sql=row["SQL"])
            processed_col = list(row.keys()).index("Processed_at") + 1
            mark_processed(sheet, i, processed_col)

def train_documents():
    sheet = Workbook_name.worksheet("Documents")
    rows = sheet.get_all_records()

    print("\n Training Document Rows")

    for j, row in enumerate(rows, start=2):

        # 1. Read required fields
        created_at = row.get("Created_at")
        processed_at = row.get("Processed_at")
        doc_text = row.get("Documents", "").strip()

        # 2. Skip rows WITHOUT created date
        if not created_at:
            continue

        # 3. Skip rows already processed
        if processed_at:
            continue

        # 4. Skip empty document rows
        if not doc_text:
            continue

        # 5. Train Vanna
        vn.train(documentation=doc_text)

        # 6. Mark processed
        processed_col = list(row.keys()).index("Processed_at") + 1
        mark_processed(sheet, j, processed_col)


    
if __name__ == "__main__":
    
    train_q_sql()
    train_documents()
    print(f"\n✅Training completed at {datetime.now().isoformat()}!")