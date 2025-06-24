#!/usr/bin/env python3
import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import XSD
from colorama import Fore, Style, init

init(autoreset=True)

print(f"{Fore.CYAN}📥 Lecture des données capteurs...{Style.RESET_ALL}")

with open('scripts/sensor_data.json') as f:
    entries = json.load(f)

g = Graph()
ns = Namespace("http://example.org/organic#")

print(f"{Fore.CYAN}🔄 Traitement de {len(entries)} échantillons...{Style.RESET_ALL}")

for e in entries:
    farm = URIRef(ns + e['farm'])
    sample = URIRef(ns + "Sample_" + e['farm'] + "_" + e['id'])
    g.add((farm, ns.hasSoilSample, sample))
    g.add((sample, ns.hasPesticide, URIRef(ns + e['pesticide'])))
    g.add((sample, ns.hasValue, Literal(e['value'], datatype=XSD.float)))

g.serialize(destination='data/farm_data.ttl', format='turtle')
print(f"{Fore.GREEN}✅ Import terminé: {len(entries)} lectures capteurs traitées{Style.RESET_ALL}")
print(f"{Fore.GREEN}💾 Données sauvegardées dans data/farm_data.ttl{Style.RESET_ALL}")