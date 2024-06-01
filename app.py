from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from nltk import word_tokenize
from flask import Flask, request, jsonify
import csv, os, re
import pytesseract as tess
from PIL import Image
import mysql.connector
import subprocess

app = Flask(__name__)

cars = pd.read_csv('data/dataset.csv')
problems = pd.read_csv('data/problems-solutions.csv')
credentials = 'data/accounts.csv'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'secret'

tess.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form.get('keyword')
    price = request.form.get('price')

    if price:
        filtered_cars = [car for _, car in cars.iterrows() if (keyword.lower() in car['Car Make'].lower() or keyword.lower() in car['Car Model'].lower()) and (float(re.sub(r'[^\d.]', '', car['Price (in USD)'])) <= float(price))]
    else:
        filtered_cars = [car for _, car in cars.iterrows() if keyword.lower() in car['Car Make'].lower() or keyword.lower() in car['Car Model'].lower()]

    return render_template('filter.html', filtered_cars=filtered_cars)

def autoAid(keyword):
    filtered_data = problems[problems['Problem'].str.contains(keyword, case=False)]
    
    return filtered_data[['Symptom', 'Possible Solution', 'Category']]

@app.route('/search-problems', methods=['POST'])
def search_problems():
    keyword = request.form.get('keyword')

    filtered_data = autoAid(keyword)

    print(f'Keyword: {keyword}')

    return render_template('filter.html', filtered_data=filtered_data)

@app.route('/filter-by-dealer', methods=['POST'])
def filter_by_dealer():
    dealer = request.form.get('dealer')

    filtered_cars = problems[problems['Dealer'] == dealer]

    print(f'Filtering by Dealer: {dealer}')

    return render_template('filter.html', filtered_cars=filtered_cars)
@app.route('/home')
def home():
    return render_template('home.html')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/autoaid')
def autoaid():
    return render_template('autoaid.html')

@app.route('/carscore')
def carscore():
    return render_template('carscore.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/community')
def community():
    return render_template('onlychat.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/plateocr')
def plateocr():
    return render_template('maintenance.html')

@app.route('/carscorefunc', methods=['POST'])
def carscorefunc():
    kmdrive = request.form['kmdrive']
    avg = request.form['avg']
    byear = request.form['byear']
    ctype = request.form['type']

    current = 10
    yeardiff = 2024 - int(byear)
    days = yeardiff * 365

    if ctype.lower() == 'diesel':
        current *= 1.2
    elif ctype.lower() == 'petrol':
        current *= 1.1
    elif ctype.lower() == 'cng':
        current *= 1.3

    average = current * days
    caravg = float(avg) * days

    score = ( caravg / average ) * 100

    if score > 100:
        score = 100

    return render_template('filter.html', car_score=score, byear=byear, ctype=ctype)

@app.route('/suggest_solutions', methods=['POST'])
def suggest_solutions():
    keyword = request.form.get('keyword')
    words = word_tokenize(keyword.lower())

    problems = pd.read_csv('data/problems-solutions.csv')
    suggestions = []

    for _ , row in problems.iterrows():
        prob = row['Problem']
        tokens = word_tokenize(prob.lower())

        if any(i in tokens for i in words):
            suggestions.append(row.to_dict())
            continue

    return render_template('filter.html', suggestions=suggestions)

@app.route('/signupverify', methods=['GET', 'POST'])
def signupverify():
    if request.method == 'POST':
        fname = request.form['fullname']
        email = request.form['mail']
        password = request.form['pass']
        cPass = request.form['confirm-password']

        if password != cPass:
            return render_template('signup.html')

        if os.path.exists(credentials):
            with open(credentials, mode='r', newline='') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header
                for row in reader:
                    if row[1] == email:  # If the email is already registered
                        return render_template('signup.html', message="Email already registered")

        with open(credentials, mode='a', newline='') as file:
            writer = csv.writer(file)
            if file.tell() == 0:  # If file is empty, write the header
                writer.writerow(['Full Name', 'Email', 'Password'])
            writer.writerow([fname, email, password])

    return render_template('home.html')

@app.route('/loginverify', methods=['GET', 'POST'])
def loginverify():
    if request.method == 'POST':
        email = request.form['mail']
        password = request.form['pass']

        with open(credentials, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Email'] == email and row['Password'] == password:
                    return render_template('home.html')

    return render_template('login.html')

@app.route('/filterParts', methods=['POST'])
def filterParts():
    keyword = request.form.get('keyword')
    
    df = pd.read_csv('data/parts.csv')
    filtered_products = df[df['Car Part'].str.contains(keyword, case=False)]
    products = filtered_products.to_dict(orient='records')

    return render_template('filter.html', products=products)

def filterLogs(txt):
    connection = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "74432",
        database = "wemech"
    )
    cursor = connection.cursor()
    query = f"SELECT * FROM maintenancelogs WHERE plate_number = %s"
    cursor.execute(query, (txt,))

    logs = cursor.fetchall()
    cursor.close()
    connection.close()

    df = pd.DataFrame(logs, columns=['log_id', 'plate_number', 'date_of_service', 'type_of_service', 'service_provider'])

    return df

@app.route('/maintenancelog', methods=['GET', 'POST'])
def maintenancelog():
    if request.method == 'POST':
        file = request.files['imageFile']
        if file:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            image = Image.open(filename)
            
            text = tess.image_to_string(image)
            cleaned = ""

            for i in text:
                if not i.isspace():
                    cleaned += i

            df = filterLogs(cleaned)
            logs = df.to_dict(orient='records')

            return render_template('filter.html', logs=logs)
    return render_template('maintenance.html')

@app.route('/runcsharp', methods=['GET'])
def runcsharp():
    result = subprocess.run(['app.exe'], capture_output=True, text=True)

    output = result.stdout

    return output

if __name__ == '__main__':
    app.run(debug=True)