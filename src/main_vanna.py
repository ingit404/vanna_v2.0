
from dotenv import load_dotenv
from src.vanna_sql import MyVanna 
from src.config  import load_config
from vanna.flask import VannaFlaskApp
import os,flask

#loading the .env file

load_dotenv()
print('.env file is loaded  successfully!✅')

#instantiating the vanna class

config=load_config()
print('Configuration loaded✅')
vn=MyVanna(config=config)

#connecting it to the database

host = os.getenv("REDSHIFT_HOST")
dbname = os.getenv("REDSHIFT_DB")
user = os.getenv("REDSHIFT_USER")
password = os.getenv("REDSHIFT_PASSWORD")
port = os.getenv("REDSHIFT_PORT", 5439) 

vn.connect_to_postgres(
    host=host,
    dbname=dbname,
    user=user,
    password=password,
    port=int(port))
print("Connected to Redshift✅")


#the UI for the users
app = VannaFlaskApp(vn, allow_llm_to_see_data=True,
                    csv_download=True,
                    chart=False,
                    redraw_chart=False,
                    summarization=False,
                    title='Welcome to Vanna.AI')

port = int(os.environ.get("PORT", 5000))  
app.run(host="0.0.0.0", port=port)

print("✅Flask app is running on port", port)











