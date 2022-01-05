import os

from flask import Flask, render_template, request, jsonify
import sqlalchemy
import json
import google.cloud.logging
import logging

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
    # [START cloud_sql_mysql_sqlalchemy_create_socket]
    # Remember - storing secrets in plaintext is potentially unsafe. Consider using
    # something like https://cloud.google.com/secret-manager/docs/overview to help keep
    # secrets secret.
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    db_socket_dir = os.environ.get("DB_SOCKET_DIR", "/cloudsql")
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # mysql+pymysql://<db_user>:<db_pass>@/<db_name>?unix_socket=<socket_path>/<cloud_sql_instance_name>
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,  # e.g. "my-database-user"
            password=db_pass,  # e.g. "my-database-password"
            database=db_name,  # e.g. "my-database-name"
            query={
                "unix_socket": "{}/{}".format(
                    db_socket_dir,  # e.g. "/cloudsql"
                    instance_connection_name)  # i.e "<PROJECT-NAME>:<INSTANCE-REGION>:<INSTANCE-NAME>"
            }
        ),
        **db_config
    )
    # [END cloud_sql_mysql_sqlalchemy_create_socket]

    return pool

@app.route('/')
def hello():
    try:
        global db
        db = init_connection_engine()
    except Exception as e:
        return str(e)
    
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
        
        logging.warning(query)
        
        with db.connect() as conn:
            conn.execute(query)
        
        """ with db.connect() as conn:
            query_pk = "SELECT patient_pk FROM patients WHERE email = " + email
            logging.warning(query_pk)
            pk_set = conn.execute(query_pk) # use fetchall()
        
         for row in pk_set:
            logging.warning(row)
        
        logging.warning(str(pk_set))

        return jsonify({"pk":pk_set})
        """

        # later a pk would be returned
        return jsonify({"pk": "patient created!"})

    except Exception as e2:
        return jsonify({"pk": str(e2)})



if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
