#!/bin/bash

echo 'Configuration de Jena Fuseki avec raisonnement sémantique...'

# Ensure clean state
rm -rf /fuseki/databases/organic_db
mkdir -p /fuseki/databases/organic_db

cat > /tmp/fuseki-config.ttl << 'EOF'
@prefix :        <#> .
@prefix fuseki:  <http://jena.apache.org/fuseki#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix tdb2:    <http://jena.apache.org/2016/tdb#> .
@prefix ja:      <http://jena.hpl.hp.com/2005/11/Assembler#> .

:service_tdb_inf a fuseki:Service ;
    rdfs:label "TDB2 organic dataset with inference" ;
    fuseki:dataset :tdb_dataset_inf ;
    fuseki:name "organic" ;
    fuseki:serviceQuery "sparql" ;
    fuseki:serviceQuery "query" ;
    fuseki:serviceReadGraphStore "get" ;
    fuseki:serviceReadWriteGraphStore "data" ;
    fuseki:serviceUpdate "update" ;
    fuseki:serviceUpload "upload" .

:tdb_dataset_inf a ja:RDFDataset ;
    ja:defaultGraph :inf_model .

:inf_model a ja:InfModel ;
    ja:baseModel :tdb_base_model ;
    ja:reasoner [
        ja:reasonerURL <http://jena.hpl.hp.com/2003/GenericRuleReasoner> ;
        ja:rules [
            ja:rulesFrom <file:///staging/jena/organic_rules.rules>
        ]
    ] .

:tdb_base_model a tdb2:GraphTDB2 ;
    tdb2:location "/fuseki/databases/organic_db" .
EOF

echo 'Démarrage du serveur Fuseki/jena'
/jena-fuseki/fuseki-server --config=/tmp/fuseki-config.ttl &
FUSEKI_PID=$!

echo 'Attente du démarrage de Fuseki/jena...'
for i in {1..30}; do
    if curl -s http://localhost:3030/$/ping > /dev/null; then
        echo 'Fuseki/jena est prêt!'
        break
    fi
    echo "Attente de Fuseki/jena... (tentative $i/30)"
    sleep 2
done

# Wait for server to be fully ready
sleep 5

# Load the ontology first
echo 'Chargement de lontologie...'
curl -X POST \
    -H "Content-Type: application/rdf+xml" \
    -T /staging/ontology/organic.owl \
    http://localhost:3030/organic/data

echo 'Configuration des règles dinférence...'
mkdir -p /tmp/inference

echo 'Configuration Fuseki/jena terminée!'
echo 'Fuseki/jena disponible'

wait $FUSEKI_PID