#!/bin/bash

echo 'Configuration de Jena Fuseki avec raisonnement sémantique...'

mkdir -p /fuseki/databases/organic_db

cat > /tmp/fuseki-config.ttl << 'EOF'
@prefix :        <#> .
@prefix fuseki:  <http://jena.apache.org/fuseki#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ja:      <http://jena.hpl.hp.com/2005/11/Assembler#> .

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

:tdb_dataset_readwrite
        a             ja:RDFDataset ;
        ja:defaultGraph :tdb_graph ;
        .

:tdb_graph
        a             ja:MemoryModel ;
        ja:location   "/fuseki/databases/organic_db" ;
        .

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

echo 'Chargement de l ontologie...'
if [ -f "/staging/ontology/organic.owl" ]; then
    curl -X POST \
        -H "Content-Type: application/rdf+xml" \
        -u admin:admin123 \
        -T /staging/ontology/organic.owl \
        http://localhost:3030/organic/data
    echo 'Ontologie chargée avec succès'
else
    echo 'Fichier ontologie non trouvé à /staging/ontology/organic.owl'
fi

echo 'Chargement des données de ferme...'
if [ -f "/staging/data/farm_data.ttl" ]; then
    curl -X POST \
        -H "Content-Type: text/turtle" \
        -u admin:admin123 \
        -T /staging/data/farm_data.ttl \
        http://localhost:3030/organic/data
    echo 'Données de ferme chargées avec succès'
else
    echo 'Fichier données de ferme non trouvé à /staging/data/farm_data.ttl'
fi

echo 'Configuration des règles dinférence...'
mkdir -p /tmp/inference

echo 'Configuration Fuseki/jena terminée!'
echo 'Fuseki/jena disponible'

wait $FUSEKI_PID