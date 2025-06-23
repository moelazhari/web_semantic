#!/usr/bin/env bash
set -e

echo "🧹 Cleaning old TDB..."
rm -rf /jena/tdb

echo "📥 Loading ontology and data into TDB..."
tdb2.tdbloader --loc /jena/tdb /jena/ontology/organic.owl /jena/data/farm_data.ttl

echo "🧠 Running inference..."
jena-infer --model /jena/tdb --rules /jena/rules/organic_rules.swrl --output /jena/inferred.ttl

echo "🚀 Starting Fuseki with inferred data..."
fuseki-server --mem --update --file /jena/inferred.ttl /ds

echo "✅ Fuseki running at http://localhost:3030/ds"
