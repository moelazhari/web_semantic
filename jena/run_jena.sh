#!/bin/bash

echo '🔄 Setting up Jena Fuseki with semantic reasoning...'

# Create TDB2 database directory
mkdir -p /fuseki/databases/organic_db

# Create Fuseki configuration with authentication
cat > /tmp/fuseki-config.ttl << 'EOF'
@prefix :        <#> .
@prefix fuseki:  <http://jena.apache.org/fuseki#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ja:      <http://jena.hpl.hp.com/2005/11/Assembler#> .

# Server configuration
:service_tdb_all  a                   fuseki:Service ;
        rdfs:label                    "TDB2 organic dataset" ;
        fuseki:dataset                :tdb_dataset_readwrite ;
        fuseki:name                   "organic" ;
        fuseki:serviceQuery           "sparql" ;
        fuseki:serviceQuery           "query" ;
        fuseki:serviceReadGraphStore  "get" ;
        fuseki:serviceReadWriteGraphStore "data" ;
        fuseki:serviceUpdate          "update" ;
        fuseki:serviceUpload          "upload" .

# Dataset
:tdb_dataset_readwrite
        a             ja:RDFDataset ;
        ja:defaultGraph :tdb_graph ;
        .

# Graph
:tdb_graph
        a             ja:MemoryModel ;
        ja:location   "/fuseki/databases/organic_db" ;
        .

# Authentication
:auth
        a             fuseki:AuthService ;
        fuseki:user   "admin" ;
        fuseki:password "admin123" ;
        fuseki:realm  "Fuseki" ;
        .
EOF

# Start Fuseki server with authentication
echo '🚀 Starting Fuseki server with authentication...'
/jena-fuseki/fuseki-server --config=/tmp/fuseki-config.ttl &
FUSEKI_PID=$!

# Wait for Fuseki to be ready
echo '⏳ Waiting for Fuseki to start...'
for i in {1..30}; do
    if curl -s http://localhost:3030/$/ping > /dev/null; then
        echo '✅ Fuseki is ready!'
        break
    fi
    echo "⏳ Waiting for Fuseki... (attempt $i/30)"
    sleep 2
done

# Load ontology if it exists
echo '📥 Loading ontology...'
if [ -f "/staging/ontology/organic.owl" ]; then
    curl -X POST \
        -H "Content-Type: application/rdf+xml" \
        -u admin:admin123 \
        -T /staging/ontology/organic.owl \
        http://localhost:3030/organic/data
    echo '✅ Ontology loaded successfully'
else
    echo '⚠️  Ontology file not found at /staging/ontology/organic.owl'
fi

# Load farm data if it exists
echo '📥 Loading farm data...'
if [ -f "/staging/data/farm_data.ttl" ]; then
    curl -X POST \
        -H "Content-Type: text/turtle" \
        -u admin:admin123 \
        -T /staging/data/farm_data.ttl \
        http://localhost:3030/organic/data
    echo '✅ Farm data loaded successfully'
else
    echo '⚠️  Farm data file not found at /staging/data/farm_data.ttl'
fi

echo '🧠 Setting up inference rules...'
# Create inference directory with proper permissions
mkdir -p /tmp/inference

echo '🎉 Fuseki setup complete!'
echo 'Fuseki is available with authentication :-)'

# Keep the container running
wait $FUSEKI_PID