#!/usr/bin/env python3
import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import XSD

print("Lecture des données capteurs...")

with open('scripts/sensor_data.json') as f:
    entries = json.load(f)

g = Graph()
ns = Namespace("http://example.org/organic#")

print(f"Traitement de {len(entries)} échantillons...")

for e in entries:
    farm = URIRef(ns + e['farm'])
    sample = URIRef(ns + "Sample_" + e['farm'] + "_" + e['id'])
    g.add((farm, ns.hasSoilSample, sample))
    g.add((sample, ns.hasPesticide, URIRef(ns + e['pesticide'])))
    g.add((sample, ns.hasValue, Literal(e['value'], datatype=XSD.float)))

g.serialize(destination='data/farm_data.ttl', format='turtle')
print(f"Import terminé: {len(entries)} lectures capteurs traitées")
print("Données sauvegardées dans data/farm_data.ttl")