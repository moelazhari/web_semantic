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
        query = load_query('all_products.rq')
    else:
        query = load_query('product_search.rq', {'SEARCH_TERM': search_term})
    
    if not query:
        return jsonify({'error': 'Query not found'}), 500
    
    result = execute_sparql_query(query)
    
    if not result:
        return jsonify({'error': 'Failed to execute query'}), 500
    
    products = {}
    
    if 'results' in result and 'bindings' in result['results']:
        for binding in result['results']['bindings']:
            product_uri = binding.get('product', {}).get('value', '')
            
            if product_uri not in products:
                # Extract product name from URI
                product_name = product_uri.split('#')[-1].replace('_', ' ')
                # Remove "Batch1" from the name
                if product_name.endswith(" Batch1"):
                    product_name = product_name[:-7]
                
                category = binding.get('category', {}).get('value', '')
                if category:
                    category = category.split('#')[-1]
                
                status = binding.get('type', {}).get('value', 'Unknown')
                
                products[product_uri] = {
                    'product': product_uri,
                    'productName': product_name,
                    'category': category,
                    'productionDate': binding.get('productionDate', {}).get('value', ''),
                    'certificationStatus': status,
                    'batchNumber': product_uri.split('_')[-1],
                    'farm': 'Organic Farm' if status == 'Organic' else 'Conventional Farm',
                    'harvestDate': binding.get('productionDate', {}).get('value', ''),
                    'chemicalAnalysis': []
                }
            
            # Add chemical analysis if available
            chemical = binding.get('chemical', {}).get('value', '')
            if chemical:
                chemical_name = chemical.split('#')[-1]
                chem_type = binding.get('chemType', {}).get('value', '').split('#')[-1]
                value = binding.get('value', {}).get('value', '')
                max_allowed = binding.get('maxAllowed', {}).get('value', '')
                
                products[product_uri]['chemicalAnalysis'].append({
                    'chemical': chemical_name,
                    'value': value,
                    'maxAllowed': max_allowed,
                    'type': chem_type
                })
    
    return jsonify({'products': list(products.values())})

@app.route('/product/<product_id>')
def product_details(product_id):
    """Get detailed information about a specific product"""
    # Get basic product info
    query = load_query('product_details.rq', {'PRODUCT_ID': product_id})
    if not query:
        return jsonify({'error': 'Query not found'}), 500
    
    result = execute_sparql_query(query)
    if not result or 'results' not in result or 'bindings' not in result['results'] or len(result['results']['bindings']) == 0:
        return jsonify({'error': 'Product not found'}), 404
    
    # Create a product info object with all required fields
    binding = result['results']['bindings'][0]
    product_uri = binding.get('product', {}).get('value', '')
    
    product_info = {
        'product': product_uri,
        'productName': product_uri.split('#')[-1].replace('_', ' ').replace(' Batch1', ''),
        'category': binding.get('category', {}).get('value', '').split('#')[-1] if 'category' in binding else 'Unknown',
        'productionDate': binding.get('productionDate', {}).get('value', '') if 'productionDate' in binding else '',
        'certificationStatus': binding.get('type', {}).get('value', 'Unknown'),
        'batchNumber': product_uri.split('_')[-1],
        'farm': 'Organic Farm' if binding.get('type', {}).get('value', '') == 'Organic' else 'Conventional Farm',
        'harvestDate': binding.get('productionDate', {}).get('value', '') if 'productionDate' in binding else '',
    }
    
    # Get chemical analysis
    chemical_analysis = []
    if 'chemical' in binding and binding['chemical']['value']:
        chemical_name = binding.get('chemical', {}).get('value', '').split('#')[-1]
        chem_type = binding.get('chemType', {}).get('value', '').split('#')[-1]
        value = binding.get('value', {}).get('value', '')
        max_allowed = binding.get('maxAllowed', {}).get('value', '')
        
        chemical_analysis.append({
            'chemical': chemical_name,
            'value': value,
            'maxAllowed': max_allowed,
            'type': chem_type
        })
    
    # For products with multiple chemicals, we need a separate query
    chemical_query = load_query('product_chemicals.rq', {'PRODUCT_ID': product_id})
    if chemical_query:
        chem_result = execute_sparql_query(chemical_query)
        if chem_result and 'results' in chem_result and 'bindings' in chem_result['results']:
            for chem_binding in chem_result['results']['bindings']:
                chemical = chem_binding.get('chemical', {}).get('value', '')
                if chemical:
                    chemical_name = chemical.split('#')[-1]
                    chem_type = chem_binding.get('chemType', {}).get('value', '').split('#')[-1]
                    value = chem_binding.get('value', {}).get('value', '')
                    max_allowed = chem_binding.get('maxAllowed', {}).get('value', '')
                    
                    # Avoid duplicates
                    if not any(chem['chemical'] == chemical_name for chem in chemical_analysis):
                        chemical_analysis.append({
                            'chemical': chemical_name,
                            'value': value,
                            'maxAllowed': max_allowed,
                            'type': chem_type
                        })
    
    return jsonify({
        'product': product_info,
        'chemicalAnalysis': chemical_analysis
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
            status = binding.get('type', {}).get('value', '')
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