#!/usr/bin/env python3
import hashlib, json
from rdflib import Graph, Namespace

ns = Namespace("http://example.org/organic#")
g = Graph()
g.parse('inferred.ttl', format='turtle')

signatures = {}
for farm in set(g.subjects(None, None)):
    sub = Graph()
    for s, p, o in g.triples((farm, None, None)):
        sub.add((s, p, o))
    data = sub.serialize(format='nt')
    sig = hashlib.sha256(data.encode('utf-8')).hexdigest()
    key = farm.split('#')[-1]
    signatures[key] = sig

with open('signatures.json','w') as f:
    json.dump(signatures, f, indent=2)

print(f"✅ Wrote {len(signatures)} signatures to signatures.json")
