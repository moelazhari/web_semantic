#!/usr/bin/env python3
import os

def load_query(query_name):
    queries_dir = os.path.dirname(os.path.abspath(__file__))
    query_file = os.path.join(queries_dir, f"{query_name}.rq")
    
    if not os.path.exists(query_file):
        raise FileNotFoundError(f"Query file not found: {query_file}")
    
    with open(query_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

def load_swrl_rules():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rules_dir = os.path.join(os.path.dirname(current_dir), 'rules')
    rules_file = os.path.join(rules_dir, "organic_rules.swrl")
    
    if not os.path.exists(rules_file):
        raise FileNotFoundError(f"SWRL rules file not found: {rules_file}")
    
    with open(rules_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

def load_verification_queries():
    organic_query = load_query("organic_farms")
    non_organic_query = load_query("non_organic_farms")
    
    return organic_query, non_organic_query 