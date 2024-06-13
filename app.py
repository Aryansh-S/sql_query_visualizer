from flask import Flask, request, render_template, jsonify, redirect, url_for
import sqlite3
import os
import glob

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'db', 'sql'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clear_upload_folder():
    files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*'))
    for f in files:
        os.remove(f)

def execute_sql_script(db_path, sql_script):
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.executescript(sql_script)
        con.commit()
        cur.close()
        con.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    clear_upload_folder()  # Clear upload folder before each upload

    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        if file.filename.rsplit('.', 1)[1].lower() == 'sql':
            db_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename + '.db')
            with open(filepath, 'r') as sql_file:
                sql_script = sql_file.read()

            if 'DROP TABLE' in sql_script.upper():
                try:
                    con = sqlite3.connect(db_path)
                    cur = con.cursor()
                    drop_statements = [stmt.strip() for stmt in sql_script.split(';') if 'DROP TABLE' in stmt.upper()]
                    for drop_stmt in drop_statements:
                        cur.execute(drop_stmt)
                    con.commit()
                    cur.close()
                    con.close()
                except sqlite3.Error as e:
                    return jsonify({"error": str(e)})

            success, error_message = execute_sql_script(db_path, sql_script)
            if success:
                return redirect(url_for('query_page', db_file=file.filename + '.db'))
            else:
                return jsonify({"error": error_message})

        return redirect(url_for('query_page', db_file=file.filename))
    
    return redirect(url_for('index'))

@app.route('/query', methods=['GET', 'POST'])
def query_page():
    db_file = request.args.get('db_file')
    if request.method == 'POST':
        sql_query = request.form['query']
        try:
            db_path = os.path.join(app.config['UPLOAD_FOLDER'], db_file)
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute(sql_query)
            results = cur.fetchall()
            columns = [description[0] for description in cur.description]
            con.close()
            return jsonify({"columns": columns, "results": results})
        except sqlite3.Error as e:
            return jsonify({"error": str(e)})
    return render_template('query.html', db_file=db_file)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

