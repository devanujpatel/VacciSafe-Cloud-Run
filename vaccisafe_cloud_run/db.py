

class database:
    def __init__(self):
        self.db_hostname = os.environ["DB_HOST"]
        self.conn = self.init_connection_engine()
        self.vaccines = {}

    def init_connection_engine(self):

        self.db_config = {
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

        return self.init_unix_connection_engine(self.db_config)


    def init_unix_connection_engine(self, db_config):
        # [START cloud_sql_mysql_sqlalchemy_create_socket]
        # Remember - storing secrets in plaintext is potentially unsafe. Consider using
        # something like https://cloud.google.com/secret-manager/docs/overview to help keep
        # secrets secret.
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]
        db_socket_dir = os.environ.get("DB_SOCKET_DIR", "/cloudsql")
        instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

        self.pool = sqlalchemy.create_engine(
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

        return self.pool

    def make_user(self, fname, lname, email, password, external_id, mobile_number, gender, year_dob, month_dob, day_dob, blood_group, address, city):
        dob_string = year_dob+ "-" + month_dob + "-" + day_dob
        query = f"INSERT INTO patients(fname, lname, email, p_password, external_id, mobile_number, gender, dob, bloodgroup, addr, city) VALUES ('{fname}', '{lname}', '{email}', '{password}', '{email}', {mobile_number}, '{gender}', '{dob_string}', '{blood_group}', '{address}', '{city}')"
        with self.conn as conn:
            conn.execute(query)
            pk_rs = conn.execute("SELECT patient_pk FROM patients WHERE email = " + email)
        
        list = []

        for row in pk_rs:
            list.append(row)

        return list
    
    def make_records(self, pk):
        pass

    def get_vaccines(self):
        with self.conn as conn:
            self.vaccines = conn.execute("SELECT count(*) FROM vaccines")
        return self.vaccines