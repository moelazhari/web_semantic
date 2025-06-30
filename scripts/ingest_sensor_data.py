#!/usr/bin/env python3
import json
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import XSD
from colorama import Fore, Style, init

init(autoreset=True)

print(f"{Fore.CYAN}📥 Lecture des données capteurs...{Style.RESET_ALL}")

# Define which chemicals are prohibited vs allowed
PROHIBITED_CHEMICALS = {'Glyphosate', 'DDT', 'Atrazine'}
ALLOWED_CHEMICALS = {'Sulfur', 'Pyrethrin', 'CopperSulfate'}

with open('scripts/sensor_data.json') as f:
    entries = json.load(f)

g = Graph()
ns = Namespace("http://example.org/organic#")

print(f"{Fore.CYAN}🔄 Traitement de {len(entries)} échantillons...{Style.RESET_ALL}")

# First define chemical types
for chemical in PROHIBITED_CHEMICALS:
    chem_uri = URIRef(ns + chemical)
    g.add((chem_uri, RDF.type, ns.ProhibitedChemical))

for chemical in ALLOWED_CHEMICALS:
    chem_uri = URIRef(ns + chemical)
    g.add((chem_uri, RDF.type, ns.AllowedChemical))
    # Add max allowed levels
    if chemical == 'Sulfur':
        g.add((chem_uri, ns.maxAllowedLevel, Literal(0.25, datatype=XSD.float)))
    elif chemical == 'Pyrethrin':
        g.add((chem_uri, ns.maxAllowedLevel, Literal(0.15, datatype=XSD.float)))
    elif chemical == 'CopperSulfate':
        g.add((chem_uri, ns.maxAllowedLevel, Literal(0.20, datatype=XSD.float)))

for e in entries:
    product = URIRef(ns + e['product'])
    category = URIRef(ns + e['category'])
    sample = URIRef(ns + "Sample_" + e['product'] + "_" + e['id'])
    chemical = URIRef(ns + e['chemical'])
    
    # Add product type
    g.add((product, RDF.type, ns.Product))
    
    # Add product category
    g.add((product, ns.hasCategory, category))
    
    # Add sample data
    g.add((product, ns.hasSample, sample))
    g.add((sample, ns.hasChemical, chemical))
    g.add((sample, ns.hasValue, Literal(e['value'], datatype=XSD.float)))
    
    # Add production date (using current date for demonstration)
    g.add((product, ns.hasProductionDate, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

g.serialize(destination='data/farm_data.ttl', format='turtle')
print(f"{Fore.GREEN}✅ Import terminé: {len(entries)} lectures capteurs traitées{Style.RESET_ALL}")
print(f"{Fore.GREEN}💾 Données sauvegardées dans data/farm_data.ttl{Style.RESET_ALL}")