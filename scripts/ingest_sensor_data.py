#!/usr/bin/env python3
import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import XSD

with open('scripts/sensor_data.json') as f:
    entries = json.load(f)

g = Graph()
ns = Namespace("http://example.org/organic#")

for e in entries:
    farm = URIRef(ns + e['farm'])
    sample = URIRef(ns + "Sample_" + e['farm'] + "_" + e['id'])
    g.add((farm, ns.hasSoilSample, sample))
    g.add((sample, ns.hasPesticide, URIRef(ns + e['pesticide'])))
    g.add((sample, ns.hasValue, Literal(e['value'], datatype=XSD.float)))

g.serialize(destination='data/farm_data.ttl', format='turtle')
print("Ingested", len(entries), "sensor readings")