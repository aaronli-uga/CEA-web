from flask import Flask, request, render_template, jsonify, redirect, flash, send_from_directory
#from flask_basicauth import BasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
#import time, requests
import sqlite3
import os, datetime
from tools.util import *
from CEAsimulator.TomSim import TomSim

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.getcwd(), "static"))
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__, template_folder="templates")
app.config['SECRET_KEY'] = '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8' #Flask secret key
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 #limit upoad size to 1mb
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


db_path = "us_cities.db"
sql_path = "us_cities.sql"
date_format ="%Y-%m-%d"
simulator_config = os.path.abspath(os.path.join(os.getcwd(), "CEAsimulator/config.ini"))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route("/", methods=['POST', 'GET'])
def home():
    if request.method == 'POST':
        co2 = float(request.form["CO2"])
        temp = float(request.form["temperature"])
        city_id = int(request.form["city_id"])
        fruit_per_truss = int(request.form["fruit_per_truss"])
        start_date = (request.form["start_date"])
        end_date = (request.form["end_date"])
        sp_start_date = (request.form["sp_start_date"])
        sp_end_date = (request.form["sp_end_date"])
        is_supplement_light = (request.form["if_supplement"])
        supplement_light_intensity = float(request.form["light_intensity"])
        electricity_rate = float(request.form["electricity_rate"])
        if is_supplement_light == "false":
            is_supplement_light = False
        else:
            is_supplement_light = True
        start_julian_day = datetime.datetime.strptime(start_date, date_format)
        end_julian_day = datetime.datetime.strptime(end_date, date_format)
        sp_start_julian_day = datetime.datetime.strptime(sp_start_date, date_format)
        sp_end_julian_day = datetime.datetime.strptime(sp_end_date, date_format)
        start_time = int(request.form["start_time"].split(':')[0])
        end_time = int(request.form["end_time"].split(':')[0])

        start_julian_day = start_julian_day.timetuple().tm_yday
        end_julian_day = end_julian_day.timetuple().tm_yday
        
        sp_start_julian_day = sp_start_julian_day.timetuple().tm_yday
        sp_end_julian_day = sp_end_julian_day.timetuple().tm_yday
        
        
        query_location = f"""
            SELECT 
                LATITUDE, LONGITUDE 
            FROM US_CITIES 
            WHERE ID={city_id}
        """
        with sqlite3.connect(db_path) as con:
            location = pd.read_sql(query_location, con, index_col=None)
            lat = location.iloc[0]["LATITUDE"]
            lon = location.iloc[0]["LONGITUDE"]
            # output_array = location.to_json(orient="values")
            sim = TomSim(co2=co2, 
                        temperature=temp, 
                        fruit_per_truss=fruit_per_truss, 
                        lon=lon, 
                        lat=lat, 
                        start_date=start_julian_day, 
                        end_date=end_julian_day, 
                        isSupplement=is_supplement_light,
                        sp_start_date=sp_start_julian_day,
                        sp_end_date=sp_end_julian_day,
                        start_time=start_time,
                        end_time=end_time,
                        intensity=supplement_light_intensity,
                        electricity_rate=electricity_rate,
                        debug=False
                    )
            fresh_yield, dryweight_distribution, truss_growth, electricity_cost, weekly_accumulate_fresh_yield, weekly_fresh_yield = sim.start_simulation(config_path=simulator_config)
            
            return jsonify(
                latitude = lat,
                longitude = lon,
                total_yield = fresh_yield,
                leaves = dryweight_distribution["leaves"],
                organs = dryweight_distribution["organs"],
                stems = dryweight_distribution["stems"],
                roots = dryweight_distribution["roots"],                
                yielded = dryweight_distribution["yield"],
                days = truss_growth["days"],
                truss_num = truss_growth["truss_number"],
                electricity_cost = electricity_cost,
                weekly_acc_fresh_yield = weekly_accumulate_fresh_yield,
                weekly_fresh_yield = weekly_fresh_yield
            )
            

    show_states_query = "SELECT ID, STATE_NAME FROM US_STATES"
    with sqlite3.connect(db_path) as con:
        result = pd.read_sql(show_states_query, con, index_col=None)
        states_name = result['STATE_NAME']
        states_id = result['ID']
        states_info = zip(states_id, states_name)
    return render_template("growthSimulate.html", title="CEA Simulator Page", states_info=states_info)

@app.route("/city", methods=["POST", "GET"])
def select_states():
    if request.method == 'POST':
        data_type = request.form["type"]

        if data_type == "countyData":
            state_id = request.form["category_id"]
            show_county_query = f"""
                SELECT
                    DISTINCT COUNTY
                FROM US_CITIES
                WHERE ID_STATE={state_id}
                ORDER BY COUNTY ASC;
            """
            with sqlite3.connect(db_path) as con:
                result = pd.read_sql(show_county_query, con, index_col=None)
                county_name = result['COUNTY']
                output_array = county_name.to_json(orient="values")
                
        elif data_type == "cityData":
            city_info = request.form.getlist("category_id[]")
            show_city_query = f"""
                SELECT
                    ID, CITY
                FROM US_CITIES
                WHERE ID_STATE={city_info[0]} AND COUNTY='{city_info[1]}'
                ORDER BY CITY ASC;
            """
            with sqlite3.connect(db_path) as con:
                result = pd.read_sql(show_city_query, con, index_col=None)
                output_array = result.to_json(orient="values")

    return output_array

if not os.path.exists(db_path):
    create_db(db=db_path, sql_script=sql_path)

if __name__ == "__main__":
    app.run(debug=False, port=5000)