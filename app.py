import json, time, os, pandas, uuid, ast, shutil, jwt, datetime
from io import BytesIO
from flask import Flask, request, render_template, send_file, after_this_request, request_finished, jsonify
from flask_caching import Cache
from functools import wraps
from .credentials import email_1, password_1   
try:
    from .config import home_page_file, detail_page_file, individual_detail_file, error_page_file
    from .basic_extractor import extraction_pandas
    from .api_responser import *
except:
    from config import home_page_file, detail_page_file, individual_detail_file, error_page_file
    from basic_extractor import extraction_pandas
    from api_responser import *


ALLOWED_EXTENSIONS = {"xlsx"}
UPLOAD_FOLDER_NAME = "UPLOADS"
FILES_DIFF = " AND "
EXTENSION_SPLIT = ".xlsx"

app = Flask(__name__)

config = {
    "DEBUG": True,
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "localhost",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_URL": "redis://localhost:6379",
    "CACHE_DEFAULT_TIMEOUT": 86400,
}
app.config["SECRET_KEY"] = "saichandra"

app.config.from_mapping(config)
cache = Cache(app)

current_path = os.getcwd()
@app.template_filter('check_cache')
def check_cache_filter(c_key):
    return False if cache.get(c_key) else True 


def generate_jwt_token(email):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)  
    payload = {"email": email, "exp": expiration}
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return token


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        # Check if the token is blacklisted
        if token in blacklisted_tokens:
            return jsonify({'message': 'Token has been invalidated'}), 401

        try:
            payload = jwt.decode(token.split(" ")[1], app.config["SECRET_KEY"], algorithms=["HS256"])
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

    return decorated_function

def folder_creation(dt_file, schedule_file, folder_name=False):
    fpath = os.path.join(
        os.getcwd(),
        UPLOAD_FOLDER_NAME,
        dt_file.filename.lower().split(EXTENSION_SPLIT)[0]
        + FILES_DIFF
        + schedule_file.filename.lower().split(EXTENSION_SPLIT)[0],
    )
    if folder_name:
        return fpath
    if not os.path.exists(fpath):
        os.makedirs(
            UPLOAD_FOLDER_NAME
            + "/"
            + dt_file.filename.lower().split(EXTENSION_SPLIT)[0]
            + FILES_DIFF
            + schedule_file.filename.lower().split(EXTENSION_SPLIT)[0]
        )
        dt_file.save(
            os.path.join(
                UPLOAD_FOLDER_NAME,
                dt_file.filename.lower().split(EXTENSION_SPLIT)[0]
                + FILES_DIFF
                + schedule_file.filename.lower().split(EXTENSION_SPLIT)[0],
                dt_file.filename,
            )
        )
        schedule_file.save(
            os.path.join(
                UPLOAD_FOLDER_NAME,
                dt_file.filename.lower().split(EXTENSION_SPLIT)[0]
                + FILES_DIFF
                + schedule_file.filename.lower().split(EXTENSION_SPLIT)[0],
                schedule_file.filename,
            )
        )


def allowed_file(filename):
    # check allowable file extension
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    
    # Authenticate user (implement your own authentication logic here)
    if email == email_1 and password == password_1:
        # Generate a JWT token and return it in the resultponse
        token = generate_jwt_token(email)
        return jsonify({'message': 'Login success', 'token': token})

    return jsonify({'message': 'Invalid credentials'}), 401


def func_pandas(schedule_file, dt_file):
    # calling business logic function
    data = extraction_pandas(schedule_file, dt_file)

    home_page_data, employee_data = home_page(data['main_df']), employee_detail(data['main_df'])
   
    return ({
    "home_page_data": home_page_data,
    "logs_range": data["logs_range"],
    "invalid_count": data["invalid_count"],
    "incorrect_submission_count": data["incorrect_submission_count"],
    "satisfied_count":data["satisfied_count"],
    "incomplete_hours_count": data["incomplete_hours_count"]}, data["ivd_df"], employee_data)



@app.route("/", methods=["GET"])
def home():
    # home page api
    dirs = [{'folder_name': name, 'creation_date': os.stat(os.path.join(current_path, "UPLOADS", name)).st_mtime} for name in os.listdir("./UPLOADS") if os.path.isdir(os.path.join(current_path, "UPLOADS", name))]
    return  jsonify(dirs=dirs)


@app.route("/home/<existing>", methods=["POST"])
# @token_required
def landingpage(existing):
    
    try:
        start = time.time()
        dirs = [name for name in os.listdir("./UPLOADS") if os.path.isdir(os.path.join(current_path, "UPLOADS", name))]
        # home page api
        
        if request.method == "POST": 
            if existing=='true':
                dt_file = request.json['dt_file'].split(FILES_DIFF)[0].strip()
                dt_file_name = dt_file + '.xlsx'
                schedule_file = request.json["schedule_file"].split(FILES_DIFF)[-1].strip()
                schedule_file_name = schedule_file + '.xlsx'
                cache_key = dt_file_name + "," + schedule_file_name
                c_var = cache.get(cache_key)
                if c_var:
                    return jsonify (res=c_var, c_key=cache_key)
                else:
                    fpath = os.path.join(
                        os.getcwd(),
                        UPLOAD_FOLDER_NAME,
                        dt_file
                        + FILES_DIFF
                        + schedule_file,
                    )
                
                    res, ivd, emp = func_pandas(os.path.join(fpath, schedule_file_name), os.path.join(fpath, dt_file_name))
                    cache.set(cache_key, res)
                    cache.set(cache_key+ "," + "ivd", ivd)
                    cache.set(cache_key+ "," + "emp", emp)
                    print(time.time() - start)
                    with open(os.path.join(current_path, "API_Files", cache_key+ "," + 'emp.json'), 'w', encoding='utf-8') as f:
                        json.dump(emp, f, ensure_ascii=False, indent=4, default=str)
                    return jsonify (res=res, c_key=cache_key)
            else:
                dt_file = request.files["dt_file"]
                schedule_file = request.files["schedule_file"]
                folder_creation(dt_file, schedule_file)
                cache_key = dt_file.filename + "," + schedule_file.filename
                c_var = cache.get(cache_key)
                if c_var:
                    return jsonify (res=c_var, c_key=cache_key)

                if (
                    dt_file
                    and allowed_file(dt_file.filename)
                    and schedule_file
                    and allowed_file(schedule_file.filename)
                ):
                    res, ivd, emp = func_pandas(schedule_file, dt_file)
                    cache.set(cache_key,res)
                    
                    cache.set(cache_key+ "," + "ivd", ivd)
                    cache.set(cache_key+ "," + "emp", emp)
                    print(time.time() - start)

                    with open(os.path.join(current_path, "API_Files", cache_key+ "," + 'emp.json'), 'w', encoding='utf-8') as f:
                        json.dump(emp, f, ensure_ascii=False, indent=4, default=str)

                    return jsonify (res=res, c_key=cache_key)
                    
                return jsonify (dirs=dirs)
        
    except Exception as e:
        fname = folder_creation(dt_file, schedule_file, folder_name=True) if (type(dt_file) != str and type(schedule_file) != str) else ''
        if os.path.isdir(fname):
            shutil.rmtree(fname)
        cache.delete(cache_key)
        cache.delete(cache_key+ "," + "ivd")
        return jsonify (dirs=dirs, error=str(e))


@app.route("/detail/<index>/<c_key>", methods=["POST"])
@cache.cached(timeout=86400, query_string=True)
@token_required
def filled_fun(index, c_key):
    # import pdb;pdb.set_trace()
    if request.method == "POST":
        if cache.get(c_key+ "," + "emp"):
            return jsonify (res=cache.get(c_key+ "," + "emp")[int(index)])
        if os.path.isfile(os.path.join(current_path, "API_Files", c_key+',emp.json')):
            with open(os.path.join(current_path, "API_Files", c_key+',emp.json')) as f_in:
                data = json.load(f_in)
            return jsonify (res=data.get(index))
    dirs = [name for name in os.listdir("./UPLOADS") if os.path.isdir(os.path.join(current_path, "UPLOADS", name))]
    return jsonify (dirs=dirs)

@app.route("/clear-cache")
def clear_cache_fun():
    # clear cache
    cache.clear()
    return "Cache cleared."


@app.route("/download/<c_key>", methods=["POST"])
@token_required
def download_fun(c_key):
    try:
        df = cache.get(c_key+ "," + "ivd")
        key = str(uuid.uuid4())
        df.to_excel("invalid_logs(" +key+ ").xlsx")
        file_handle = open(os.path.join(os.getcwd(),"invalid_logs(" +key+ ").xlsx"), 'rb')
        @after_this_request
        def remove_file(response):
            try: 
                os.remove(os.path.join(os.getcwd(),"invalid_logs(" +key+ ").xlsx"))
            except Exception as e:
                print("Error: ",e)
            finally:
                file_handle.close()
            return response

        return send_file(BytesIO(file_handle.read()), mimetype="application/vnd.ms-excel")
    except:
        return jsonify({"error": "Data not found"})


@app.route("/comments", methods=["POST"])
@token_required
def add_comments():
    c_key = request.form['c_key']
    ivd_data = request.form['projectFilepath']
    if cache.get(c_key):
        redis_data = json.loads(cache.get(c_key))
    else:
        back_page_path = -2
        if request.environ.get("HTTP_REFERER").split('/')[-1] == "home":
            back_page_path = -1 
        return render_template(error_page_file, back_page_path = back_page_path)
    
    df = pandas.DataFrame([j for i in redis_data["billing_check"].values() for j in i ])
    ivd_df = pandas.DataFrame(json.loads(ivd_data))
    
    cmt_convert = ast.literal_eval(request.form['comment'])
    for key, value in cmt_convert.items():   
        df.loc[df.index[df["Employee Number"] == int(key)].tolist(), "Comments"] = value
        ivd_df.loc[ivd_df.index[ivd_df["Employee Number"] == int(key)].tolist(), "Comments"] = value
    
    df = df.groupby(by=["Employee Number"]).apply(
            lambda x: json.loads(x.to_json(orient="records"))
        )
    
    res = {
        "billing_check": df.to_dict(),
        "logs_range": {
            "logs_start": redis_data["logs_range"]["logs_start"],
            "log_end": redis_data["logs_range"]["log_end"],
        },
        "incorrect_filled_count": redis_data["incorrect_filled_count"]
    }
    cache.set(c_key, json.dumps(res))
    return jsonify (res=res, c_key=c_key, ivd = ivd_df.to_json())


blacklisted_tokens = set()

@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        # Decode the token to verify its authenticity
        payload = jwt.decode(token.split(" ")[1], app.config["SECRET_KEY"], algorithms=["HS256"])
        # Add the token to the blacklist upon logout
        blacklisted_tokens.add(token)
        return jsonify({'message': 'Logged out successfully'})
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token'}), 401
    

if __name__ == "__main__":
    app.run()

   

