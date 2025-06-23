echo '🔄 Setting up Jena Fuseki with semantic reasoning...'
        
# Create TDB2 database
mkdir -p /fuseki/databases/organic_db

# Load ontology and data
echo '📥 Loading ontology...'
tdb2.tdbloader --loc=/fuseki/databases/organic_db /staging/ontology/organic.owl

echo '📥 Loading farm data...'
tdb2.tdbloader --loc=/fuseki/databases/organic_db /staging/data/farm_data.ttl

echo '🧠 Running SPARQL inference rules...'
# Create inference queries for organic certification
mkdir -p /staging/inference

# Start Fuseki server
echo '🚀 Starting Fuseki server...'
/jena-fuseki/fuseki-server --loc=/fuseki/databases/organic_db --update /organic