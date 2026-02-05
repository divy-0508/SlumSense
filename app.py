from flask import Flask, render_template, request, jsonify,session
import requests
import sqlite3
import time
import os
import json
import pandas as pd
import pickle
import catboost
from datetime import datetime
from groq import Groq
import secrets,os,json

app = Flask(__name__)

# Configuration
GEOAPIFY_API_KEY = "8ff8a58f407746f6aa38d2fb8cbe2549"
DB_FILE = 'slumsense.db'
USERS_FILE = 'users.json'
app.secret_key = secrets.token_hex(16)

client = Groq(api_key="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")
# Load Analytics Data
try:
    city_df = pd.read_csv("city_data.csv")
except Exception as e:
    print(f"Warning: Could not load city_data.csv. Analytics may not work. Error: {e}")
    city_df = pd.DataFrame(columns=["city_name", "date", "temperature_c", "available_water_kl", "water_stress_index", "required_water_kl", "daily_water_complaints", "daily_resolved_complaints"])

# Load Prediction Model
risk_model = None
stress_model = None
try:
    with open('model_1.pkl', 'rb') as f:
        risk_model = pickle.load(f)
    print("Risk prediction model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model_1.pkl. Predictions will not work. Error: {e}")

try:
    with open('model_2.pkl', 'rb') as f:
        stress_model = pickle.load(f)
    print("Stress prediction model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model_2.pkl. Stress predictions will not work. Error: {e}")

garbage_model = None
try:
    with open('model_3.pkl', 'rb') as f:
        garbage_model = pickle.load(f)
    print("Garbage prediction model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model_3.pkl. Garbage predictions will not work. Error: {e}")

overflow_model = None
try:
    with open('model_4.pkl', 'rb') as f:
        overflow_model = pickle.load(f)
    print("Overflow prediction model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model_4.pkl. Overflow predictions will not work. Error: {e}")

risk_score_model = None
try:
    with open('model_5.pkl', 'rb') as f:
        risk_score_model = pickle.load(f)
    print("Risk Score prediction model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model_5.pkl. Risk Score predictions will not work. Error: {e}")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS complaints
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lat REAL,
                     lon REAL,
                     city TEXT,
                     category TEXT,
                     description TEXT,
                     timestamp INTEGER,
                     user_phone TEXT)''')
    
    # Simple migration for existing DBs
    try:
        conn.execute("ALTER TABLE complaints ADD COLUMN user_phone TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists

    try:
        conn.execute("ALTER TABLE complaints ADD COLUMN city TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists

    conn.commit()
    conn.close()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {"residents": [], "government_officials": []}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Initialize DB on startup
init_db()

@app.route('/')
def home():
    return render_template('slumsense-website.html')

@app.route('/map')
def index():
    return render_template('index.html', api_key=GEOAPIFY_API_KEY)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/resident-dashboard')
def resident_dashboard():
    return render_template('resident-dashboard.html')

@app.route('/government-dashboard')
def government_dashboard():
    cities = []
    if not city_df.empty and "city_name" in city_df.columns:
        cities = sorted(city_df["city_name"].unique())
    return render_template('government-dashboard.html', cities=cities)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        
        # Initialize chat history in session if not exists
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Add user message to history
        session['chat_history'].append({
            "role": "user",
            "content": user_message
        })
        
        # Get response from Groq
        chat_completion = client.chat.completions.create(
            messages=session['chat_history'],
            model="llama-3.1-8b-instant",  # Fast and free model
            temperature=0.7,
            max_tokens=1024,
        )
        
        assistant_message = chat_completion.choices[0].message.content
        
        # Add assistant response to history
        session['chat_history'].append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Keep only last 10 messages to avoid token limits
        if len(session['chat_history']) > 10:
            session['chat_history'] = session['chat_history'][-10:]
        
        session.modified = True
        
        return jsonify({
            'response': assistant_message,
            'success': True
        })
    
    except Exception as e:
        return jsonify({
            'response': f'Error: {str(e)}',
            'success': False
        }),request,session

@app.route('/get_analytics_data')
def get_analytics_data():
    city = request.args.get("city")
    category = request.args.get("category", "water")
    
    if city_df.empty:
        return jsonify({"error": "No data available"}), 404

    d = (
        city_df[city_df["city_name"] == city]
        .sort_values("date")
        .tail(7)
    )

    if d.empty:
         return jsonify({"error": "City not found"}), 404

    dates = d["date"].astype(str).tolist()
    
    import random

    if category == 'drainage':
        # Mock Drainage Data
        efficiency = [random.randint(60, 90) for _ in range(7)]
        blockages = [random.randint(5, 20) for _ in range(7)]
        total_complaints = [random.randint(10, 30) for _ in range(7)]
        solved_complaints = [int(c * random.uniform(0.5, 0.9)) for c in total_complaints]
        
        return jsonify({
            "dates": dates,
            "metrics": {
                "efficiency": {
                    "title": "Drainage Efficiency (%)",
                    "values": efficiency,
                    "latest": efficiency[-1]
                },
                "blockages": {
                    "title": "Reported Blockages",
                    "values": blockages,
                    "latest": blockages[-1]
                },
                "total_complaints": {
                    "title": "Total Complaints",
                    "values": total_complaints,
                    "latest": total_complaints[-1]
                },
                "solved_complaints": {
                    "title": "Solved Complaints",
                    "values": solved_complaints,
                    "latest": solved_complaints[-1]
                }
            },
            "comparison": {
                "title": "Drainage Efficiency vs Blockages",
                "metricA": "efficiency",
                "metricB": "blockages"
            },
            "primary_metric": "efficiency"
        })

    elif category == 'electricity':
        # Mock Electricity Data
        avg_voltage = [random.randint(210, 240) for _ in range(7)]
        outages = [random.randint(0, 5) for _ in range(7)]
        total_complaints = [random.randint(5, 25) for _ in range(7)]
        solved_complaints = [int(c * random.uniform(0.6, 0.95)) for c in total_complaints]

        return jsonify({
            "dates": dates,
            "metrics": {
                "voltage": {
                    "title": "Avg Voltage (V)",
                    "values": avg_voltage,
                    "latest": avg_voltage[-1]
                },
                "outages": {
                    "title": "Power Outages (hrs)",
                    "values": outages,
                    "latest": outages[-1]
                },
                "total_complaints": {
                    "title": "Total Complaints",
                    "values": total_complaints,
                    "latest": total_complaints[-1]
                },
                "solved_complaints": {
                    "title": "Solved Complaints",
                    "values": solved_complaints,
                    "latest": solved_complaints[-1]
                }
            },
            "comparison": {
                "title": "Voltage Stability vs Outages",
                "metricA": "voltage",
                "metricB": "outages"
            },
            "primary_metric": "voltage"
        })

    elif category == 'sanitation':
        # Mock Sanitation Data
        cleanliness_index = [random.randint(4, 9) for _ in range(7)] # Scale 1-10
        waste_collected = [random.randint(500, 800) for _ in range(7)] # Tons
        total_complaints = [random.randint(15, 40) for _ in range(7)]
        solved_complaints = [int(c * random.uniform(0.4, 0.8)) for c in total_complaints]

        return jsonify({
            "dates": dates,
            "metrics": {
                "cleanliness": {
                    "title": "Cleanliness Index (1-10)",
                    "values": cleanliness_index,
                    "latest": cleanliness_index[-1]
                },
                "waste": {
                    "title": "Waste Collected (Tons)",
                    "values": waste_collected,
                    "latest": waste_collected[-1]
                },
                "total_complaints": {
                    "title": "Total Complaints",
                    "values": total_complaints,
                    "latest": total_complaints[-1]
                },
                "solved_complaints": {
                    "title": "Solved Complaints",
                    "values": solved_complaints,
                    "latest": solved_complaints[-1]
                }
            },
            "comparison": {
                "title": "Cleanliness vs Waste Collection",
                "metricA": "cleanliness",
                "metricB": "waste"
            },
            "primary_metric": "cleanliness"
        })

    else:
        # Default Water Data (Existing Logic)
        return jsonify({
            "dates": dates,
            "metrics": {
                "temperature": {
                    "title": "Temperature (°C)",
                    "values": d["temperature_c"].tolist(),
                    "latest": float(d["temperature_c"].iloc[-1])
                },
                "available": {
                    "title": "Available Water",
                    "values": d["available_water_kl"].tolist(),
                    "latest": float(d["available_water_kl"].iloc[-1])
                },
                "index": {
                    "title": "Water stress index",
                    "values": d["water_stress_index"].tolist(),
                    "latest": float(d["water_stress_index"].iloc[-1])
                },
                "required_water": {
                    "title": "Required Water",
                    "values": d["required_water_kl"].tolist(),
                    "latest": float(d["required_water_kl"].iloc[-1])
                },
                "total_complaints": {
                    "title": "Total Complaints",
                    "values": d["daily_water_complaints"].tolist(),
                    "latest": int(d["daily_water_complaints"].iloc[-1])
                },
                "solved_complaints": {
                    "title": "Solved Complaints",
                    "values": d["daily_resolved_complaints"].tolist(),
                    "latest": int(d["daily_resolved_complaints"].iloc[-1])
                }
            },
            "comparison": {
                "title": "Water Availability vs Requirement",
                "metricA": "available",
                "metricB": "required_water"
            },
            "primary_metric": "index"
        })

@app.route('/api/predict_risk', methods=['POST'])
def predict_risk():
    if not risk_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    data = request.json
    city = data.get('city')
    date_str = data.get('date')
    available_water = data.get('available_water')
    
    if not city or not date_str or available_water is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Construct input vector matching: ['city_name', 'available_water_kl', 'year', 'month', 'day']
        # Note: CatBoost usually takes a specific format. If passed as list, order matters.
        # If the model was trained with DataFrame, passing a list might warn but work, or require a list of lists.
        features = [city, float(available_water), year, month, day]
        
        prediction = risk_model.predict(features)
        
        return jsonify({
            "prediction": prediction,
            "inputs": {
                "city": city,
                "date": date_str,
                "available_water": available_water
            }
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict_stress', methods=['POST'])
def predict_stress():
    if not stress_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    data = request.json
    city = data.get('city')
    date_str = data.get('date')
    available_water = data.get('available_water')
    avg_supply_hours = data.get('avg_supply_hours')
    temperature = data.get('temperature')
    
    if not city or not date_str or available_water is None or avg_supply_hours is None or temperature is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Construct input vector matching: 
        # ['city_name', 'available_water_kl', 'avg_water_supply_hours', 'temperature_c', 'year', 'month', 'day']
        features = [city, float(available_water), float(avg_supply_hours), float(temperature), year, month, day]
        
        prediction = stress_model.predict(features)
        
        return jsonify({
            "prediction": prediction,
            "inputs": {
                "city": city,
                "date": date_str,
                "available_water": available_water,
                "avg_supply_hours": avg_supply_hours,
                "temperature": temperature
            }
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict_garbage', methods=['POST'])
def predict_garbage():
    if not garbage_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    data = request.json
    city = data.get('city')
    date_str = data.get('date')
    vehicles = data.get('vehicles')
    bins = data.get('bins')
    
    if not city or not date_str or vehicles is None or bins is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Construct input vector matching: 
        # ['city_name', 'collection_vehicles_available', 'no_of_bins_available', 'year', 'month', 'day']
        features = [city, float(vehicles), float(bins), year, month, day]
        
        prediction = garbage_model.predict(features)
        
        return jsonify({
            "prediction": prediction,
            "inputs": {
                "city": city,
                "date": date_str,
                "vehicles": vehicles,
                "bins": bins
            }
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict_overflowing_bins', methods=['POST'])
def predict_overflowing_bins():
    if not overflow_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    data = request.json
    city = data.get('city')
    date_str = data.get('date')
    vehicles = data.get('vehicles')
    bins = data.get('bins')
    complaints = data.get('complaints')
    
    if not city or not date_str or vehicles is None or bins is None or complaints is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Construct input vector matching: 
        # ['city_name', 'collection_vehicles_available', 'no_of_bins_available', 'no_of_garbage_complaints', 'year', 'month', 'day']
        features = [city, float(vehicles), float(bins), float(complaints), year, month, day]
        
        prediction = overflow_model.predict(features)
        
        return jsonify({
            "prediction": prediction,
            "inputs": {
                "city": city,
                "date": date_str,
                "vehicles": vehicles,
                "bins": bins,
                "complaints": complaints
            }
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict_risk_score', methods=['POST'])
def predict_risk_score():
    if not risk_score_model:
        return jsonify({"error": "Model not loaded"}), 500
    
    data = request.json
    city = data.get('city')
    date_str = data.get('date')
    vehicles = data.get('vehicles')
    bins = data.get('bins')
    complaints = data.get('complaints')
    garbage_collected = data.get('garbage_collected')
    
    if not city or not date_str or vehicles is None or bins is None or complaints is None or garbage_collected is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Construct input vector matching: 
        # ['city_name', 'collection_vehicles_available', 'no_of_bins_available', 'no_of_garbage_complaints', 'garbage_collected_kg', 'year', 'month', 'day']
        features = [city, float(vehicles), float(bins), float(complaints), float(garbage_collected), year, month, day]
        
        prediction = risk_score_model.predict(features)
        
        return jsonify({
            "prediction": prediction,
            "inputs": {
                "city": city,
                "date": date_str,
                "vehicles": vehicles,
                "bins": bins,
                "complaints": complaints,
                "garbage_collected": garbage_collected
            }
        })
    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    users = load_users()
    
    user_type = data.get('type', 'resident') # Default to resident if not specified

    if user_type == 'government':
        # Check if user already exists
        for user in users['government_officials']:
            if user['email'] == data['email']:
                return jsonify({"error": "Official email already registered"}), 400
        
        new_user = {
            "name": data['name'],
            "email": data['email'],
            "password": data['password'], # In production, hash this!
            "department": data['department']
        }
        users['government_officials'].append(new_user)
        save_users(users)
        return jsonify({"success": True, "message": "Official account created successfully"})

    else:
        # Resident Logic
        # Check if user already exists
        for user in users['residents']:
            if user['phone'] == data['phone']:
                return jsonify({"error": "User already exists"}), 400
                
        new_user = {
            "name": data['name'],
            "phone": data['phone'],
            "password": data['password'], # In production, hash this!
            "area": data['area']
        }
        
        users['residents'].append(new_user)
        save_users(users)
        return jsonify({"success": True, "message": "Account created successfully"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    users = load_users()
    user_type = data.get('type')
    
    if user_type == 'resident':
        for user in users['residents']:
            if user['phone'] == data['phone'] and user['password'] == data['password']:
                return jsonify({"success": True, "user": user})
    elif user_type == 'government':
        # For demo purposes, allow any government login if not in file, or add default admin
        # Here we just check the file
        for user in users['government_officials']:
            if user['email'] == data['email'] and user['password'] == data['password']:
                return jsonify({"success": True, "user": user})
        
        # fallback for demo: Create a default admin if list is empty and credentials match
        if not users['government_officials'] and data['email'] == 'admin@gov.in' and data['password'] == 'admin123':
             return jsonify({"success": True, "user": {"name": "Admin", "email": "admin@gov.in", "type": "government"}})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/user_complaints', methods=['GET'])
def get_user_complaints():
    phone = request.args.get('phone')
    if not phone:
        return jsonify([])
    
    try:
        conn = get_db_connection()
        complaints = conn.execute('SELECT * FROM complaints WHERE user_phone = ? ORDER BY timestamp DESC', (phone,)).fetchall()
        conn.close()
        
        result = []
        for row in complaints:
            result.append({
                "id": row['id'],
                "category": row['category'],
                "description": row['description'],
                "location": f"{row['lat']}, {row['lon']}",
                "city": row['city'] if 'city' in row.keys() else "Unknown",
                "date": time.strftime('%Y-%m-%d', time.localtime(row['timestamp'])),
                "status": "Pending" # Placeholder status
            })
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching user complaints: {e}")
        return jsonify([])

@app.route('/api/all_complaints', methods=['GET'])
def get_all_complaints():
    try:
        conn = get_db_connection()
        complaints = conn.execute('SELECT * FROM complaints ORDER BY timestamp DESC').fetchall()
        conn.close()
        
        result = []
        for row in complaints:
            result.append({
                "id": row['id'],
                "category": row['category'],
                "description": row['description'],
                "location": f"{row['lat']}, {row['lon']}",
                "city": row['city'] if 'city' in row.keys() else "Unknown",
                "date": time.strftime('%Y-%m-%d', time.localtime(row['timestamp'])),
                "status": "Pending", # Placeholder status
                "user_phone": row['user_phone']
            })
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching all complaints: {e}")
        return jsonify([])

@app.route('/search', methods=['GET'])
def search_proxy():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    api_url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": query,
        "apiKey": GEOAPIFY_API_KEY,
        "limit": 5,
        "lang": "en"
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_env_data', methods=['GET'])
def get_env_data():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        lat_float = float(lat)
        lon_float = float(lon)

        # 1. Fetch Temperature
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        weather_resp = requests.get(weather_url)
        weather_data = weather_resp.json()
        temp = weather_data.get('current', {}).get('temperature_2m', 'N/A')
        temp_unit = weather_data.get('current_units', {}).get('temperature_2m', '°C')

        # 2. Fetch AQI
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi"
        aqi_resp = requests.get(aqi_url)
        aqi_data = aqi_resp.json()
        aqi = aqi_data.get('current', {}).get('us_aqi', 'N/A')

        # 3. Fetch Local Complaints (Approx 2km radius)
        conn = get_db_connection()
        range_deg = 0.02 
        complaints_query = conn.execute('''
            SELECT category, description, timestamp 
            FROM complaints 
            WHERE lat BETWEEN ? AND ? 
            AND lon BETWEEN ? AND ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (lat_float - range_deg, lat_float + range_deg, lon_float - range_deg, lon_float + range_deg)).fetchall()
        conn.close()

        complaints_list = []
        for row in complaints_query:
            complaints_list.append({
                "category": row['category'],
                "description": row['description'],
                "date": time.strftime('%Y-%m-%d', time.localtime(row['timestamp']))
            })

        return jsonify({
            "temperature": temp,
            "temperature_unit": temp_unit,
            "aqi": aqi,
            "complaints": complaints_list
        })

    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"error": "Failed to fetch environmental data"}), 500

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    data = request.json
    if not data or 'lat' not in data or 'lon' not in data or 'category' not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO complaints (lat, lon, city, category, description, timestamp, user_phone) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (data['lat'], data['lon'], data.get('city', ''), data['category'], data.get('description', ''), int(time.time()), data.get('user_phone')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error saving complaint: {e}")
        return jsonify({"error": "Failed to save complaint"}), 500

@app.route('/get_heatmap_data', methods=['GET'])
def get_heatmap_data():
    try:
        conn = get_db_connection()
        # Fetch all complaints coordinates
        complaints = conn.execute('SELECT lat, lon FROM complaints').fetchall()
        conn.close()

        # Format as list of [lat, lon, intensity]
        # Intensity 0.5 ensures that a single point isn't immediately "hot red", 
        # but overlapping points will build up to red.
        heatmap_points = [[row['lat'], row['lon'], "1"] for row in complaints]
        
        return jsonify(heatmap_points)
    except Exception as e:
        print(f"Error fetching heatmap data: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)