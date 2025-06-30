#!/usr/bin/env python3
import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'queries'))

from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
from query_loader import load_query
from colorama import Fore, Style, init

init(autoreset=True)

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
        print(f"{Fore.CYAN}📁 Dossier créé: {REPORTS_DIR}{Style.RESET_ALL}")

def generate_compliance_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("compliance_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    products_data = []
    for result in results["results"]["bindings"]:
        product_name = result["product"]["value"].split("#")[-1]
        category = result["category"]["value"].split("#")[-1]
        sample_name = result["sample"]["value"].split("#")[-1]
        chemical = result["chemical"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        cert_status = result.get("certStatus", {}).get("value", "N/A")
        violation = result.get("violationReason", {}).get("value", "N/A")
        
        products_data.append({
            "Produit": product_name,
            "Catégorie": category,
            "Echantillon": sample_name,
            "Substance_Chimique": chemical,
            "Concentration": value,
            "Statut_Certification": cert_status,
            "Raison_Violation": violation
        })
    
    df = pd.DataFrame(products_data)
    
    if not df.empty:
        # Save detailed report as CSV
        report_file = os.path.join(REPORTS_DIR, "rapport_conformite.csv")
        df.to_csv(report_file, index=False)
        print(f"{Fore.GREEN}✅ Rapport de conformité sauvegardé: {report_file}{Style.RESET_ALL}")
        
        # Generate summary
        summary = {
            "total_products": len(df["Produit"].unique()),
            "organic_products": len(df[df["Statut_Certification"] == "CERTIFIED"]["Produit"].unique()),
            "non_organic_products": len(df[df["Statut_Certification"] == "REJECTED"]["Produit"].unique()),
            "by_category": df.groupby("Catégorie")["Produit"].nunique().to_dict(),
            "violations": len(df[df["Raison_Violation"] != "N/A"]["Produit"].unique()),
            "timestamp": datetime.now().isoformat()
        }
        
        summary_file = os.path.join(REPORTS_DIR, "resume_conformite.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"{Fore.GREEN}✅ Résumé sauvegardé: {summary_file}{Style.RESET_ALL}")
        
        return summary
    else:
        print(f"{Fore.YELLOW}⚠️ Aucune donnée de produit trouvée. Création d'un rapport vide.{Style.RESET_ALL}")
        return {
            "total_products": 0,
            "organic_products": 0,
            "non_organic_products": 0,
            "by_category": {},
            "violations": 0,
            "timestamp": datetime.now().isoformat()
        }

def generate_violation_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("violation_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    violations = []
    for result in results["results"]["bindings"]:
        product_name = result["product"]["value"].split("#")[-1]
        category = result["category"]["value"].split("#")[-1]
        chemical = result["chemical"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        reason = result.get("violationReason", {}).get("value", "N/A")
        
        violations.append({
            "product": product_name,
            "category": category,
            "chemical": chemical,
            "value": value,
            "violation_reason": reason
        })
    
    if violations:
        print(f"{Fore.RED}⚠️ {len(violations)} violations détectées{Style.RESET_ALL}")
        return violations
    else:
        print(f"{Fore.YELLOW}⚠️ Aucune violation détectée{Style.RESET_ALL}")
        return []

def generate_certification_report():
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("certification_report")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    certifications = []
    for result in results["results"]["bindings"]:
        product_name = result["product"]["value"].split("#")[-1]
        category = result["category"]["value"].split("#")[-1]
        status = result.get("certStatus", {}).get("value", "N/A")
        cert_date = result.get("certDate", {}).get("value", "N/A")
        prod_date = result.get("productionDate", {}).get("value", "N/A")
        
        certifications.append({
            "product": product_name,
            "category": category,
            "status": status,
            "certification_date": cert_date,
            "production_date": prod_date
        })
    
    if certifications:
        print(f"{Fore.GREEN}✅ {len(certifications)} certifications trouvées{Style.RESET_ALL}")
        return certifications
    else:
        print(f"{Fore.YELLOW}⚠️ Aucune certification trouvée{Style.RESET_ALL}")
        return []

def create_audit_trail(compliance_summary, violations, certifications):
    """Create audit trail with all certification activities"""
    
    audit_trail = {
        "timestamp": datetime.now().isoformat(),
        "summary": compliance_summary,
        "violations": violations,
        "certifications": certifications
    }
    
    audit_file = os.path.join(REPORTS_DIR, "piste_audit.json")
    with open(audit_file, 'w') as f:
        json.dump(audit_trail, f, indent=2)
    
    print(f"{Fore.GREEN}✅ Piste d'audit sauvegardée: {audit_file}{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}📝 Génération des rapports de conformité{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔍 Analyse des données de certification bio\n{Style.RESET_ALL}")
    
    try:
        ensure_reports_directory()
        
        print(f"{Fore.CYAN}1. Génération du rapport de conformité...{Style.RESET_ALL}")
        compliance_summary = generate_compliance_report()
        
        print(f"{Fore.CYAN}\n2. Génération du rapport de violations...{Style.RESET_ALL}")
        violations = generate_violation_report()
        
        print(f"{Fore.CYAN}\n3. Génération du rapport de certification...{Style.RESET_ALL}")
        certifications = generate_certification_report()
        
        print(f"{Fore.CYAN}\n4. Création de la piste d'audit...{Style.RESET_ALL}")
        create_audit_trail(compliance_summary, violations, certifications)
        
        print(f"{Fore.CYAN}\nRésumé de la génération:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Produits totaux: {compliance_summary['total_products']}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   Produits bio: {compliance_summary['organic_products']}{Style.RESET_ALL}")
        print(f"{Fore.RED}   Produits non-bio: {compliance_summary['non_organic_products']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Violations détectées: {compliance_summary['violations']}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   Certifications: {len(certifications)}{Style.RESET_ALL}")
        
        if compliance_summary['by_category']:
            print(f"{Fore.YELLOW}\nProduits par catégorie:{Style.RESET_ALL}")
            for category, count in compliance_summary['by_category'].items():
                print(f"{Fore.YELLOW}   {category}: {count}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}\nGénération des rapports terminée avec succès!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Consultez le dossier 'reports/' pour les fichiers générés{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors de la génération des rapports: {e}{Style.RESET_ALL}")
        raise

if __name__ == "__main__":
    main()