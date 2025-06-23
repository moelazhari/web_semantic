#!/bin/bash

echo "🔍 Checking Fuseki health..."

# Check if Fuseki is responding
if curl -s http://localhost:3030/$/ping > /dev/null; then
    echo "✅ Fuseki is running"
else
    echo "❌ Fuseki is not responding"
    exit 1
fi

# Check if the dataset exists
if curl -s http://localhost:3030/organic/query?query=SELECT%20*%20WHERE%20%7B%20?s%20?p%20?o%20%7D%20LIMIT%201 > /dev/null; then
    echo "✅ Dataset is accessible"
else
    echo "❌ Dataset is not accessible"
    exit 1
fi

# Count triples in the dataset
TRIPLE_COUNT=$(curl -s -H "Accept: application/sparql-results+json" \
    "http://localhost:3030/organic/query?query=SELECT%20%28COUNT%28*%29%20AS%20%3Fcount%29%20WHERE%20%7B%20?s%20?p%20?o%20%7D" | \
    grep -o '"value":"[^"]*"' | cut -d'"' -f4)

echo "📊 Dataset contains $TRIPLE_COUNT triples"

echo "🎉 Health check passed!" 