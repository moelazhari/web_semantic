#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from colorama import Fore, Style, init
init(autoreset=True)

app = Flask(__name__)

# Fuseki endpoint - use Docker service URL when in container
FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030') + "/organic/query"

def load_query(query_file, replacements=None):
    """Load SPARQL query from file with optional replacements"""
    try:
        with open(f'queries/{query_file}', 'r') as f:
            query = f.read()
        
        if replacements:
            for key, value in replacements.items():
                query = query.replace(f"{{{{{key}}}}}", value)
        
        return query
    except FileNotFoundError:
        print(f"{Fore.RED}❌ Query file {query_file} not found{Style.RESET_ALL}")
        return None

def execute_sparql_query(query):
    """Execute SPARQL query against Fuseki"""
    try:
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        
        response = requests.post(FUSEKI_URL, data=query, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}❌ Error executing SPARQL query: {e}{Style.RESET_ALL}")
        return None

@app.route('/')
def index():
    """Main search page"""
    return render_template('index.html')

@app.route('/search')
def search_products():
    """Search products by name"""
    search_term = request.args.get('q', '')
    
    if not search_term:
        # Return all products if no search term
        query = load_query('all_products.rq')
    else:
        # Search for specific products
        query = load_query('product_search.rq', {'SEARCH_TERM': search_term})
    
    if not query:
        return jsonify({'error': 'Query not found'}), 500
    
    result = execute_sparql_query(query)
    
    if not result:
        return jsonify({'error': 'Failed to execute query'}), 500
    
    # Process results
    products = []
    if 'results' in result and 'bindings' in result['results']:
        for binding in result['results']['bindings']:
            product = {}
            for var, value in binding.items():
                if value['type'] == 'uri':
                    # Extract local name from URI
                    product[var] = value['value'].split('#')[-1] if '#' in value['value'] else value['value'].split('/')[-1]
                else:
                    product[var] = value['value']
            products.append(product)
    
    return jsonify({'products': products})

@app.route('/product/<product_id>')
def product_details(product_id):
    """Get detailed information about a specific product"""
    # Get basic product info
    query = load_query('product_search.rq', {'SEARCH_TERM': product_id})
    if not query:
        return jsonify({'error': 'Query not found'}), 500
    
    result = execute_sparql_query(query)
    if not result or 'results' not in result or 'bindings' not in result['results']:
        return jsonify({'error': 'Product not found'}), 404
    
    product_info = None
    for binding in result['results']['bindings']:
        if binding.get('product', {}).get('value', '').endswith(product_id):
            product_info = {}
            for var, value in binding.items():
                if value['type'] == 'uri':
                    product_info[var] = value['value'].split('#')[-1] if '#' in value['value'] else value['value'].split('/')[-1]
                else:
                    product_info[var] = value['value']
            break
    
    if not product_info:
        return jsonify({'error': 'Product not found'}), 404
    
    # Get violations if any
    violations_query = load_query('product_violations.rq', {'PRODUCT_ID': product_id})
    violations = []
    
    if violations_query:
        violations_result = execute_sparql_query(violations_query)
        if violations_result and 'results' in violations_result and 'bindings' in violations_result['results']:
            for binding in violations_result['results']['bindings']:
                violation = {}
                for var, value in binding.items():
                    if value['type'] == 'uri':
                        violation[var] = value['value'].split('#')[-1] if '#' in value['value'] else value['value'].split('/')[-1]
                    else:
                        violation[var] = value['value']
                violations.append(violation)
    
    return jsonify({
        'product': product_info,
        'violations': violations
    })

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    # Get all products
    query = load_query('all_products.rq')
    if not query:
        return jsonify({'error': 'Query not found'}), 500
    
    result = execute_sparql_query(query)
    if not result:
        return jsonify({'error': 'Failed to execute query'}), 500
    
    total_products = 0
    organic_products = 0
    non_organic_products = 0
    
    if 'results' in result and 'bindings' in result['results']:
        total_products = len(result['results']['bindings'])
        for binding in result['results']['bindings']:
            status = binding.get('certificationStatus', {}).get('value', '')
            if status == 'Organic':
                organic_products += 1
            elif status == 'Non-Organic':
                non_organic_products += 1
    
    return jsonify({
        'total_products': total_products,
        'organic_products': organic_products,
        'non_organic_products': non_organic_products
    })

if __name__ == '__main__':
    print(f"{Fore.GREEN}🌐 Démarrage de l'interface web...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📱 Interface disponible sur: http://0.0.0.0:5000{Style.RESET_ALL}")
    app.run(debug=True, host='0.0.0.0', port=5000) 