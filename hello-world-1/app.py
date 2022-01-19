import os

from flask import Flask, render_template, request, jsonify
import sqlalchemy
import json
import google.cloud.logging
import logging
import math
import datetime

app = Flask(__name__)

# Instantiates a client
client = google.cloud.logging.Client()
client.setup_logging()
# Emits the data using the standard logging module
logging.warning("HEY THERE!")

db_hostname = os.environ["DB_HOST"]

def init_connection_engine():

    db_config = {
        # [START cloud_sql_mysql_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        "pool_size": 5,
        # Temporarily exceeds the set pool_size if no connections are available.
        "max_overflow": 2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # [END cloud_sql_mysql_sqlalchemy_limit]

        # [START cloud_sql_mysql_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection attempts,
        # but provides no arguments for configuration.
        # [END cloud_sql_mysql_sqlalchemy_backoff]

        # [START cloud_sql_mysql_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        "pool_timeout": 30,  # 30 seconds
        # [END cloud_sql_mysql_sqlalchemy_timeout]

        # [START cloud_sql_mysql_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished
        "pool_recycle": 1800,  # 30 minutes
        # [END cloud_sql_mysql_sqlalchemy_lifetime]

    }

    return init_unix_connection_engine(db_config)


def init_unix_connection_engine(db_config):
    
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    db_socket_dir = os.environ.get("DB_SOCKET_DIR", "/cloudsql")
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,  
            password=db_pass,  
            database=db_name, 
            query={
                "unix_socket": "{}/{}".format(
                    db_socket_dir,  
                    instance_connection_name)  
            }
        ),
        **db_config
    )

    return pool


db = init_connection_engine()

def check_id(user_email, user_password):

    pwd_query = "SELECT p_password FROM patients WHERE email = '" +user_email+"'"

    with db.connect() as conn:
        stored_password = conn.execute(pwd_query).fetchall()

    if stored_password:
        try:
            stored_password = stored_password[0][0]
            if user_password == stored_password:
                return True
            else:
                return False
        except:
            return "error"
    else:
        return "error"


@app.route('/')
def hello():

    with db.connect() as conn:
        vaccines = conn.execute(
            "SELECT count(*) FROM vaccines"
        ).fetchall()

    return str(vaccines)

@app.route('/register', methods=["POST"])
def register():
    try:
        global db
        db = init_connection_engine()
    except Exception as e:
        return str(e)

    try:
        user_data = request.json 
        email = user_data['email']
        password = user_data['password']
        fname = user_data['fname']
        lname = user_data['lname']
        mobile_number = int(user_data['mobile_number'])
        gender = user_data['gender']
        year_dob = user_data['year_dob']
        month_dob = user_data['month_dob']
        day_dob = user_data['day_dob']
        blood_group = user_data['blood_group']
        address = user_data['address']
        city = user_data['city']
        dob_string = year_dob+ "-" + month_dob + "-" + day_dob
        
        query = f"INSERT INTO patients(fname, lname, email, p_password, external_id, mobile_number, gender, dob, bloodgroup, addr, city) VALUES ('{fname}', '{lname}', '{email}', '{password}', '{email}', {mobile_number}, '{gender}', '{dob_string}', '{blood_group}', '{address}', '{city}')"
        query_pk = "SELECT patient_pk FROM patients WHERE email = '" + email + "'"

        logging.warning(query)
        logging.warning(query_pk)

        with db.connect() as conn:
            conn.execute(query)
            pk_set = conn.execute(query_pk).fetchall()

            logging.warning(pk_set)

        # send pk and email to android
        return jsonify({"pk":pk_set[0][0], "email":email})

    except Exception as e2:
        return jsonify({"pk": str(e2), "email":"error!"})

@app.route('/log_in', methods=["POST", "GET"])
def log_in():

    user_credentials = request.json 
    user_email = user_credentials["email"]
    user_password = str(user_credentials["password"])

    result = check_id(user_email, user_password)
     
    if result == True:
        return jsonify({"is_valid": "true"})
    elif result == False:
        return jsonify({"is_valid": "false"})
    else:
        return jsonify({"is_valid": "no record found"})
    

"""
------------------------------------------------
Vaccines:
year: 3
month: 2
weeks: 3
"""


def make_vaccine_date(dob_date_obj, vaccines_master_tuples):

    dob_date_obj = datetime.datetime.combine(dob_date_obj, datetime.time(0, 0))
    # this is a list containin dictionaries about vaccines (since tuples are immutable!)
    vaccines_master = []

    for vaccine in vaccines_master_tuples:
        vaccines_master.append({"pk":vaccine[0],"name":vaccine[1], "date_v":None, "disease":vaccine[2], "details":vaccine[5], "gender":vaccine[6], "reminder_date":None, "vac_taken_date":None})
        ymw_string = vaccine[3]
        # sample vaccine date: 00y00m06w
        years = ymw_string[0:2]
        if years[0] == "0":
            years = years[1]
        years = int(years)
        months = ymw_string[3:5]
        if months[0] == "0":
            months = months[1]
        months = int(months)
        weeks = ymw_string[6:8]
        if weeks[0] == "0":
            weeks = weeks[1]
        weeks = int(weeks)

        # as per the data entries done in the database:
        # we have 14 weeks and 0 months as the faulty entries and then the correct combinations of vaccine dates
        # possible faulty combinations to be converted into proper ones: 0 months and 6, 10 or 14 weeks
        if weeks == 6:
            months += 1
            days = 14
        elif weeks == 10:
            months += 2
            days = 14
        elif weeks == 14:
            months += 3
            days = 14
        else:
            days = weeks * 7
        
        date_v = datetime.datetime(int(dob_date_obj.strftime("%Y")) + years, int(dob_date_obj.strftime("%m")) + months, int(dob_date_obj.strftime("%d")) + days)
        
        vaccines_master[-1]["date_v"] = date_v

        if date_v > dob_date_obj:
            vaccines_master[-1]["reminder_date"] = date_v
        else:
            vaccines_master[-1]["vac_taken_date"] = dob_date_obj

        logging.info(vaccines_master)

    return vaccines_master

def get_insert_date(date):
    # convert datetime obj to a yyyy-mm-dd format (in string)
    return str(date.strftime("%Y")) + "-" + str(date.strftime("%m")) + "-" + str(date.strftime("%d"))


def get_recommended_vaccines(email):
    # get dob of patient
    with db.connect() as conn:
        dob = conn.execute("SELECT dob FROM patients WHERE email = '"+email+"'")
        all_vaccines = conn.execute("SELECT * FROM vaccines")
        patient_pk = conn.execute("SELECT patient_pk FROM patients WHERE email = '"+email+"'")

    for pk in patient_pk:
        patient_pk = pk[0]
    
    logging.info(patient_pk)

    logging.info("all vaccines coming up")
    
    # this is a list which contains tuples containing data of vaccines
    vaccines_master = []
    for row in all_vaccines:
        logging.info(row)
        vaccines_master.append(row)

    logging.info(vaccines_master)
    # cursor is not as such subscriptable
    # the loop will run only once fetching the value of dob for us
    for row in dob:
        logging.warning("loop running")
        logging.warning(row)
        dob = row[0]

    #logging.info(str(all_vaccines))
    logging.warning("LOOK HERE")
    logging.info(str(type(dob)))
    logging.info(dob)

    vaccines_master = make_vaccine_date(dob, vaccines_master)

    with db.connect() as conn:
        for vaccine in vaccines_master:
            
            vaccine_fk = vaccine["pk"]

            if vaccine["reminder_date"] == None:
                date = get_insert_date(vaccine["vac_taken_date"])
                query = f"INSERT INTO appt_records(vaccine_fk, patient_fk, vac_taken_date) VALUES ({vaccine_fk}, {patient_pk}, '{date}')"
            else:
                date = get_insert_date(vaccine["reminder_date"])
                query = f"INSERT INTO appt_records(vaccine_fk, patient_fk, reminder_date) VALUES ({vaccine_fk}, {patient_pk}, '{date}')"
            
            conn.execute(query)

    return jsonify({"vaccine_data":vaccines_master})


@app.route("/recommended_vaccines", methods=["GET", "POST"])
def recommended_vaccines():
    user_credentials = request.json 
    user_email = user_credentials["email"]
    user_password = str(user_credentials["password"])
    
    result = check_id(user_email, user_password)

    if result == True:
        result_set = get_recommended_vaccines(user_email)
        return result_set

    elif result == False:
        return "wrong identity"
    else:
        return "error"


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
