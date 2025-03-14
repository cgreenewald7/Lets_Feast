from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from recipe_scrapers import scrape_me
import os

app = Flask(__name__, static_folder='static')

# Initialize SQLite database with a unique constraint on name
def init_db():
    with sqlite3.connect('recipes.db', timeout=10) as conn:  # Set timeout to 10 seconds
        c = conn.cursor()
        # Comment out DROP TABLE after running once to reset
        # c.execute('DROP TABLE IF EXISTS recipes')
        c.execute('''CREATE TABLE IF NOT EXISTS recipes (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL UNIQUE,
                     ingredients TEXT,
                     instructions TEXT,
                     image TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS meal_plan (
                     date TEXT PRIMARY KEY,
                     recipe_name TEXT)''')
        conn.commit()

# Serve the HTML frontend
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

# API to get all recipes
@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    with sqlite3.connect('recipes.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, ingredients, instructions, image FROM recipes')
        recipes = [{'id': r[0], 'name': r[1], 'ingredients': r[2], 'instructions': r[3], 'image': r[4]} for r in c.fetchall()]
    return jsonify(recipes)

# API to add a recipe
@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    data = request.json
    with sqlite3.connect('recipes.db', timeout=10) as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO recipes (name, ingredients, instructions, image) VALUES (?, ?, ?, ?)',
                      (data['name'], data['ingredients'], data['instructions'], data.get('image', '/images/variety.webp')))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Recipe name already exists'}), 400
    return jsonify({'message': 'Recipe added'}), 201

# API to scrape a recipe from a URL
@app.route('/api/scrape', methods=['POST'])
def scrape_recipe():
    data = request.json
    url = data.get('url')
    try:
        scraper = scrape_me(url)
        recipe = {
            'name': scraper.title(),
            'ingredients': '\n'.join(scraper.ingredients()),
            'instructions': scraper.instructions(),
            'image': '/images/variety.webp'
        }
        with sqlite3.connect('recipes.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO recipes (name, ingredients, instructions, image) VALUES (?, ?, ?, ?)',
                      (recipe['name'], recipe['ingredients'], recipe['instructions'], recipe['image']))
            conn.commit()
        return jsonify(recipe), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Recipe name already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# API to update a recipe
@app.route('/api/recipes/<int:id>', methods=['PUT'])
def update_recipe(id):
    data = request.json
    with sqlite3.connect('recipes.db', timeout=10) as conn:
        c = conn.cursor()
        try:
            c.execute('UPDATE recipes SET name=?, ingredients=?, instructions=?, image=? WHERE id=?',
                      (data['name'], data['ingredients'], data['instructions'], data.get('image'), id))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Updated name conflicts with an existing recipe'}), 400
    return jsonify({'message': 'Recipe updated'})

# API to delete a recipe
@app.route('/api/recipes/<int:id>', methods=['DELETE'])
def delete_recipe(id):
    with sqlite3.connect('recipes.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM recipes WHERE id=?', (id,))
        if c.rowcount == 0:
            return jsonify({'error': 'Recipe not found'}), 404
        conn.commit()
    return jsonify({'message': 'Recipe deleted'})

# API to get/set meal plan
@app.route('/api/meal_plan', methods=['GET', 'POST'])
def manage_meal_plan():
    with sqlite3.connect('recipes.db', timeout=10) as conn:
        c = conn.cursor()
        if request.method == 'GET':
            c.execute('SELECT date, recipe_name FROM meal_plan')
            meal_plan = {r[0]: r[1] for r in c.fetchall()}
            return jsonify(meal_plan)
        else:  # POST
            data = request.json
            c.execute('DELETE FROM meal_plan')  # Clear existing meal plan
            for date, recipe_name in data.items():
                c.execute('INSERT INTO meal_plan (date, recipe_name) VALUES (?, ?)', (date, recipe_name))
            conn.commit()
    return jsonify({'message': 'Meal plan saved'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)  # Enable threading