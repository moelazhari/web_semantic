#!/bin/bash

echo 'Configuration de Jena Fuseki avec raisonnement sémantique...'

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
        ja:rules :rule_set ;
        ja:schema [
            ja:baseModel :tdb_base_model ;
            ja:rules :rule_set
        ]
    ] .

:rule_set a ja:RuleSet ;
    rdfs:label "Organic certification rules" ;
    ja:rulesFrom <file:///staging/jena/organic_rules.rules> .

:tdb_base_model a tdb2:GraphTDB2 ;
    tdb2:location "/fuseki/databases/organic_db" .

:auth
    a             fuseki:AuthService ;
    fuseki:user   "admin" ;
    fuseki:password "admin123" ;
    fuseki:realm  "Fuseki" ;
    .
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

# Clear existing data first
echo 'Nettoyage des données existantes...'
curl -X DELETE -u admin:admin123 http://localhost:3030/organic/data

# Load the ontology first
echo 'Chargement de lontologie...'
curl -X POST \
    -H "Content-Type: application/rdf+xml" \
    -u admin:admin123 \
    -T /staging/ontology/organic.owl \
    http://localhost:3030/organic/data

# Wait for the data file
echo 'Attente du fichier farm_data.ttl...'
while [ ! -f /staging/data/farm_data.ttl ]; do
    sleep 2
done

# Function to load farm data
load_farm_data() {
    echo 'Chargement des données de ferme...'
    curl -X POST \
        -H "Content-Type: text/turtle" \
        -u admin:admin123 \
        -T /staging/data/farm_data.ttl \
        http://localhost:3030/organic/data
    echo 'Données de ferme chargées avec succès'
}

# Initial load
load_farm_data

# Monitor for changes and reload
LAST_MODIFIED=$(stat -c %Y /staging/data/farm_data.ttl)
while true; do
    sleep 1
    CURRENT_MODIFIED=$(stat -c %Y /staging/data/farm_data.ttl)
    if [ "$CURRENT_MODIFIED" != "$LAST_MODIFIED" ]; then
        echo 'Changement détecté dans farm_data.ttl, rechargement...'
        # Clear existing data first
        curl -X DELETE -u admin:admin123 http://localhost:3030/organic/data
        # Reload ontology and data
        curl -X POST \
            -H "Content-Type: application/rdf+xml" \
            -u admin:admin123 \
            -T /staging/ontology/organic.owl \
            http://localhost:3030/organic/data
        load_farm_data
        LAST_MODIFIED=$CURRENT_MODIFIED
    fi
done &

echo 'Configuration des règles dinférence...'
mkdir -p /tmp/inference

echo 'Configuration Fuseki/jena terminée!'
echo 'Fuseki/jena disponible'

wait $FUSEKI_PID