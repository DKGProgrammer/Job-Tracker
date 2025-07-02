# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
def init_db():
    with sqlite3.connect('jobtracker.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        company TEXT,
                        position TEXT,
                        status TEXT,
                        date_applied TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')

# User authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        with sqlite3.connect('jobtracker.db') as conn:
            try:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return 'Username already exists.'
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('jobtracker.db') as conn:
            user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                return redirect(url_for('dashboard'))
            return 'Invalid credentials.'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Dashboard and CRUD
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('jobtracker.db') as conn:
        apps = conn.execute('SELECT * FROM applications WHERE user_id=?', (session['user_id'],)).fetchall()
    return render_template('dashboard.html', applications=apps)

@app.route('/add', methods=['POST'])
def add():
    if 'user_id' in session:
        data = (session['user_id'], request.form['company'], request.form['position'], request.form['status'], request.form['date_applied'])
        with sqlite3.connect('jobtracker.db') as conn:
            conn.execute('INSERT INTO applications (user_id, company, position, status, date_applied) VALUES (?, ?, ?, ?, ?)', data)
    return redirect(url_for('dashboard'))

@app.route('/filter_jobs',methods=['POST'])
def filter_jobs():
    if 'user_id' in session:
        if request.method == "POST":
            selectedfilter = request.form["filter_options"]
            with sqlite3.connect('jobtracker.db') as conn:
                apps = conn.execute('SELECT * FROM applications WHERE user_id=?', (session['user_id'],)).fetchall()
            
                #print(apps[0][3],selectedfilter)
                if selectedfilter == "Company":
                    apps.sort(key=myCompany)
                elif selectedfilter == "Position":
                    apps.sort(key=myPosition)
                elif selectedfilter == "Status":
                    apps.sort(key=myStatus)
                elif selectedfilter == "Date":
                    apps.sort(key=myDate)      
                    
                print(apps)          
            
        
    return render_template('dashboard.html', applications=apps)



@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' in session:
        with sqlite3.connect('jobtracker.db') as conn:
            conn.execute('DELETE FROM applications WHERE id=? AND user_id=?', (id, session['user_id']))
    return redirect(url_for('dashboard'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('jobtracker.db') as conn:
        if request.method == 'POST':
            conn.execute('''UPDATE applications SET company=?, position=?, status=?, date_applied=? 
                            WHERE id=? AND user_id=?''',
                         (request.form['company'], request.form['position'], request.form['status'], request.form['date_applied'], id, session['user_id']))
            return redirect(url_for('dashboard'))
        app = conn.execute('SELECT * FROM applications WHERE id=? AND user_id=?', (id, session['user_id'])).fetchone()
    return render_template('edit.html', app=app)

@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    query = request.args.get('q')
    with sqlite3.connect('jobtracker.db') as conn:
        apps = conn.execute('''SELECT * FROM applications WHERE user_id=? AND 
                               (company LIKE ? OR position LIKE ? OR status LIKE ?)''',
                            (session['user_id'], f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    return render_template('dashboard.html', applications=apps)

# Route to search for real job listings from Remotive
@app.route('/search_jobs', methods=['GET', 'POST'])
def search_jobs():
    if 'user_id' not in session:
        return redirect('/login')

    results = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        urlapi = f'https://remotive.com/api/remote-jobs?search={keyword}'
        response = requests.get(urlapi)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('jobs', [])
            

    return render_template('search_jobs.html', results=results)

# Route to save selected job to tracker
@app.route('/save-job', methods=['POST'])
def save_job():
    if 'user_id' not in session:
        return redirect('/login')

    company = request.form['company']
    position = request.form['position']
    status = 'Applied'
    date_applied = request.form['date_applied']

    conn = sqlite3.connect('jobtracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO applications (user_id, company, position, status, date_applied) VALUES (?, ?, ?, ?, ?)",
              (session['user_id'], company, position, status, date_applied))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

        
def myCompany(arr):
    return arr[2].lower()
def myPosition(arr):
    return arr[3].lower()
def myStatus(arr):
    return arr[4].lower()
def myDate(arr):
    return arr[5].lower()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
