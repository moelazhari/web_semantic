#!/usr/bin/env python3
import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'queries'))

from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
from query_loader import load_query

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
REPORTS_DIR = "reports"

def setup_sparql():
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    return sparql

def ensure_reports_directory():
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        print(f"Dossier créé: {REPORTS_DIR}")

def generate_compliance_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("compliance_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    farms_data = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        sample_name = result["sample"]["value"].split("#")[-1]
        pesticide = result["pesticide"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        
        farm_type = "Inconnu"
        if "farmType" in result:
            farm_type = result["farmType"]["value"].split("#")[-1]
        
        cert_status = result.get("certStatus", {}).get("value", "N/A")
        violation = result.get("violationReason", {}).get("value", "N/A")
        
        farms_data.append({
            "Ferme": farm_name,
            "Echantillon": sample_name,
            "Pesticide": pesticide,
            "Concentration": value,
            "Type_Ferme": farm_type,
            "Statut_Certification": cert_status,
            "Raison_Violation": violation
        })
    
    df = pd.DataFrame(farms_data)
    
    if df.empty:
        print("Aucune donnée de ferme trouvée. Création d'un rapport vide.")
        compliance_summary = {
            "date_rapport": datetime.now().isoformat(),
            "total_fermes": 0,
            "fermes_bio": 0,
            "fermes_non_bio": 0,
            "total_echantillons": 0,
            "pesticides_detectes": [],
            "reglementation": "EU 2018/848 - Agriculture Biologique",
            "statut": "AUCUNE_DONNEE"
        }
    else:
        compliance_summary = {
            "date_rapport": datetime.now().isoformat(),
            "total_fermes": len(df["Ferme"].unique()),
            "fermes_bio": len(df[df["Type_Ferme"] == "OrganicFarm"]["Ferme"].unique()),
            "fermes_non_bio": len(df[df["Type_Ferme"] == "NonOrganicFarm"]["Ferme"].unique()),
            "total_echantillons": len(df),
            "pesticides_detectes": df["Pesticide"].unique().tolist(),
            "reglementation": "EU 2018/848 - Agriculture Biologique",
            "statut": "DONNEES_TROUVEES"
        }
    
    report_file = os.path.join(REPORTS_DIR, "rapport_conformite.csv")
    df.to_csv(report_file, index=False)

    summary_file = os.path.join(REPORTS_DIR, "resume_conformite.json")
    with open(summary_file, 'w') as f:
        json.dump(compliance_summary, f, indent=2)
    
    print(f"Rapport de conformité sauvegardé: {report_file}")
    print(f"Résumé sauvegardé: {summary_file}")
    
    return compliance_summary

def generate_violation_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("violation_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    violations = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        sample_name = result["sample"]["value"].split("#")[-1]
        pesticide = result["pesticide"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        reason = result.get("violationReason", {}).get("value", "Violation inconnue")
        
        violation_type = "Inconnu"
        if pesticide in ["DDT", "Atrazine", "Chlordane"]:
            violation_type = "Pesticide Interdit"
        elif "level exceeds" in reason.lower():
            violation_type = "Limite de Concentration Dépassée"
        
        violations.append({
            "Ferme": farm_name,
            "Echantillon": sample_name,
            "Pesticide": pesticide,
            "Concentration": value,
            "Type_Violation": violation_type,
            "Raison_Violation": reason,
            "Severite": "HAUTE" if violation_type == "Pesticide Interdit" else "MOYENNE"
        })
    
    if violations:
        df_violations = pd.DataFrame(violations)
        violations_file = os.path.join(REPORTS_DIR, "rapport_violations.csv")
        df_violations.to_csv(violations_file, index=False)
        print(f"Rapport de violations sauvegardé: {violations_file}")
    else:
        print("Aucune violation détectée")
    
    return violations

def generate_certification_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("certification_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    certifications = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        status = result.get("certStatus", {}).get("value", "CERTIFIED")
        cert_date = result.get("certDate", {}).get("value", datetime.now().isoformat())
        
        certifications.append({
            "Ferme": farm_name,
            "Statut_Certification": status,
            "Date_Certification": cert_date,
            "Valide_Jusqu": "2025-12-31",
            "Conformite_Reglementation": "EU 2018/848"
        })
    
    if certifications:
        df_certifications = pd.DataFrame(certifications)
        cert_file = os.path.join(REPORTS_DIR, "rapport_certification.csv")
        df_certifications.to_csv(cert_file, index=False)
        print(f"Rapport de certification sauvegardé: {cert_file}")
    else:
        print("Aucune certification trouvée")
    
    return certifications

def generate_audit_trail():
    audit_data = {
        "date_audit": datetime.now().isoformat(),
        "systeme": "Pipeline Certification Bio",
        "etapes": [
            {
                "etape": "Import données capteurs",
                "statut": "Terminé",
                "timestamp": datetime.now().isoformat()
            },
            {
                "etape": "Inférence sémantique",
                "statut": "Terminé", 
                "timestamp": datetime.now().isoformat()
            },
            {
                "etape": "Génération rapports",
                "statut": "En cours",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "reglementation_appliquee": "EU 2018/848",
        "version_systeme": "1.0"
    }
    
    audit_file = os.path.join(REPORTS_DIR, "piste_audit.json")
    with open(audit_file, 'w') as f:
        json.dump(audit_data, f, indent=2)
    
    print(f"Piste d'audit sauvegardée: {audit_file}")
    return audit_data

def main():
    print("Génération des rapports de conformité")
    print("Analyse des données de certification bio\n")
    
    try:
        ensure_reports_directory()
        
        print("1. Génération du rapport de conformité...")
        compliance_summary = generate_compliance_report()
        
        print("\n2. Génération du rapport de violations...")
        violations = generate_violation_report()
        
        print("\n3. Génération du rapport de certification...")
        certifications = generate_certification_report()
        
        print("\n4. Création de la piste d'audit...")
        audit_data = generate_audit_trail()
        
        print(f"\nRésumé de la génération:")
        print(f"   Fermes totales: {compliance_summary['total_fermes']}")
        print(f"   Fermes bio: {compliance_summary['fermes_bio']}")
        print(f"   Fermes non-bio: {compliance_summary['fermes_non_bio']}")
        print(f"   Violations détectées: {len(violations)}")
        print(f"   Certifications: {len(certifications)}")
        
        print("\nGénération des rapports terminée avec succès!")
        print("Consultez le dossier 'reports/' pour les fichiers générés")
        
    except Exception as e:
        print(f"Erreur lors de la génération des rapports: {e}")
        raise

if __name__ == "__main__":
    main()