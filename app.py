from flask import Flask, render_template, jsonify, g, request
from pathlib import Path
import sqlite3

DATABASE = Path("Data") / Path("data.db")

app = Flask(__name__)

def get_db():
    """
    Retrieves or creates a connection to the SQLite database within the current request context.

    This function ensures that a single database connection is reused throughout the duration of a request.

    Returns:
        sqlite3.Connection: If a connection already exists in the request
        context, the existing connection is returned. Otherwise, a new connection is created and returned.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # To return rows as named tuples
    return db

@app.teardown_appcontext
def close_connection(exception):
    """
    Closes the SQLite connection when the request ends.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=()):
    """
    Executes a SQL query and fetches the results.

    This function executes the provided SQL query with the given arguments and returns the results.
    It automatically manages the database cursor, ensuring it is closed after fetching the results.
    Args:
        query (str): The SQL query to execute.
        args (tuple, optional): A tuple of arguments to pass to the query.
    Returns:
        list: Returns a list of all rows.
    """
    cur = get_db().cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return rv

@app.route('/')
def index():
    results = query_db("SELECT MIN(YEAR_SOLD), MAX(YEAR_SOLD) FROM ManhattanSales")

    min_year, max_year = results[0] if results else (0, 0) # Check if there was a result

    return render_template('map.html',
                            min_year=min_year,
                            max_year=max_year
                            )

@app.route('/data/<int:year>')
def get_data(year):
    try:
        # Block direct browser access
        if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render_template("error.html", message="Direct access not allowed."), 403

        # Query the sales for that year
        sales = query_db("SELECT SALE_PRICE, LATITUDE, LONGITUDE FROM ManhattanSales WHERE YEAR_SOLD = (?)", (year, ))

        # If there are no results for that year, it will be an empty map
        if not sales:
            return None
        
        # Convert to list of dictionaries containing the sale data {price, lat, long}
        sales = [dict(sale) for sale in sales]

        # Send max price that year to tune the heat map
        result = query_db("SELECT MAX(SALE_PRICE) FROM ManhattanSales")
        max_price = result[0][0] if result else 0

        return jsonify( {
            'data': sales,
            'max_price': max_price
            } )
    
    except Exception as e:
        # Return an error response if something goes wrong
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/game')
def game():
    return render_template('game.html')

if __name__ == '__main__':
    app.run(debug=True)