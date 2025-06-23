#!/usr/bin/env python3
import os
import json
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

# Configuration - use environment variable for Docker compatibility
FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
REPORTS_DIR = "reports"

def setup_sparql():
    """Setup SPARQL endpoint connection"""
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    return sparql

def ensure_reports_directory():
    """Create reports directory if it doesn't exist"""
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        print(f"📁 Created reports directory: {REPORTS_DIR}")

def generate_compliance_report():
    """Generate comprehensive compliance report"""
    sparql = setup_sparql()
    
    # Query for all farm data
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?farm ?farmType ?sample ?pesticide ?value ?certStatus ?violationReason WHERE {
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        
        OPTIONAL {
            ?farm rdf:type ?farmType .
            FILTER(?farmType IN (:OrganicFarm, :NonOrganicFarm))
        }
        
        OPTIONAL { ?farm :certificationStatus ?certStatus }
        OPTIONAL { ?farm :hasViolationReason ?violationReason }
    }
    ORDER BY ?farm ?sample
    """
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    # Process results
    farms_data = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        sample_name = result["sample"]["value"].split("#")[-1]
        pesticide = result["pesticide"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        
        farm_type = "Unknown"
        if "farmType" in result:
            farm_type = result["farmType"]["value"].split("#")[-1]
        
        cert_status = result.get("certStatus", {}).get("value", "N/A")
        violation = result.get("violationReason", {}).get("value", "N/A")
        
        farms_data.append({
            "Farm": farm_name,
            "Sample": sample_name,
            "Pesticide": pesticide,
            "Concentration": value,
            "Farm_Type": farm_type,
            "Certification_Status": cert_status,
            "Violation_Reason": violation
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(farms_data)
    
    # Handle empty DataFrame
    if df.empty:
        print("⚠️  No farm data found. Creating empty report.")
        compliance_summary = {
            "report_date": datetime.now().isoformat(),
            "total_farms": 0,
            "organic_farms": 0,
            "non_organic_farms": 0,
            "total_samples": 0,
            "pesticides_detected": [],
            "regulation": "EU 2018/848 - Organic Agriculture",
            "status": "NO_DATA"
        }
    else:
        # Generate compliance summary
        compliance_summary = {
            "report_date": datetime.now().isoformat(),
            "total_farms": len(df["Farm"].unique()),
            "organic_farms": len(df[df["Farm_Type"] == "OrganicFarm"]["Farm"].unique()),
            "non_organic_farms": len(df[df["Farm_Type"] == "NonOrganicFarm"]["Farm"].unique()),
            "total_samples": len(df),
            "pesticides_detected": df["Pesticide"].unique().tolist(),
            "regulation": "EU 2018/848 - Organic Agriculture",
            "status": "DATA_FOUND"
        }
    
    # Save detailed report
    report_file = os.path.join(REPORTS_DIR, "compliance_report.csv")
    df.to_csv(report_file, index=False)
    
    # Save summary
    summary_file = os.path.join(REPORTS_DIR, "compliance_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(compliance_summary, f, indent=2)
    
    print(f"📊 Compliance report saved: {report_file}")
    print(f"📋 Summary saved: {summary_file}")
    
    return compliance_summary

def generate_violation_report():
    """Generate detailed violation report"""
    sparql = setup_sparql()
    
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?sample ?pesticide ?value ?violationReason WHERE {
        ?farm rdf:type :NonOrganicFarm .
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        OPTIONAL { ?farm :hasViolationReason ?violationReason }
    }
    ORDER BY ?farm
    """
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    violations = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        sample_name = result["sample"]["value"].split("#")[-1]
        pesticide = result["pesticide"]["value"].split("#")[-1]
        value = float(result["value"]["value"])
        reason = result.get("violationReason", {}).get("value", "Unknown violation")
        
        # Determine violation type
        violation_type = "Unknown"
        if pesticide in ["DDT", "Atrazine", "Chlordane"]:
            violation_type = "Prohibited Pesticide"
        elif "level exceeds" in reason.lower():
            violation_type = "Concentration Limit Exceeded"
        
        violations.append({
            "Farm": farm_name,
            "Sample": sample_name,
            "Pesticide": pesticide,
            "Concentration": value,
            "Violation_Type": violation_type,
            "Violation_Reason": reason,
            "Severity": "HIGH" if violation_type == "Prohibited Pesticide" else "MEDIUM"
        })
    
    if violations:
        df_violations = pd.DataFrame(violations)
        violations_file = os.path.join(REPORTS_DIR, "violations_report.csv")
        df_violations.to_csv(violations_file, index=False)
        print(f"⚠️  Violations report saved: {violations_file}")
    else:
        print("✅ No violations detected")
    
    return violations

def generate_certification_report():
    """Generate certification status report"""
    sparql = setup_sparql()
    
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?certStatus ?certDate WHERE {
        ?farm rdf:type :OrganicFarm .
        OPTIONAL { ?farm :certificationStatus ?certStatus }
        OPTIONAL { ?farm :certificationDate ?certDate }
    }
    ORDER BY ?farm
    """
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    certifications = []
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        status = result.get("certStatus", {}).get("value", "CERTIFIED")
        cert_date = result.get("certDate", {}).get("value", datetime.now().isoformat())
        
        certifications.append({
            "Farm": farm_name,
            "Certification_Status": status,
            "Certification_Date": cert_date,
            "Valid_Until": "2025-12-31",  # Assuming 1-year validity
            "Regulation_Compliance": "EU 2018/848"
        })
    
    if certifications:
        df_cert = pd.DataFrame(certifications)
        cert_file = os.path.join(REPORTS_DIR, "certification_report.csv")
        df_cert.to_csv(cert_file, index=False)
        print(f"🏆 Certification report saved: {cert_file}")
    
    return certifications

def generate_audit_trail():
    """Generate audit trail for blockchain verification"""
    sparql = setup_sparql()
    
    # Get all farm data for audit trail
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?farmType ?sample ?pesticide ?value WHERE {
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        
        OPTIONAL {
            ?farm rdf:type ?farmType .
            FILTER(?farmType IN (:OrganicFarm, :NonOrganicFarm))
        }
    }
    ORDER BY ?farm
    """
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    audit_data = {
        "audit_timestamp": datetime.now().isoformat(),
        "regulation": "EU 2018/848",
        "farms": {}
    }
    
    for result in results["results"]["bindings"]:
        farm_name = result["farm"]["value"].split("#")[-1]
        
        if farm_name not in audit_data["farms"]:
            audit_data["farms"][farm_name] = {
                "samples": [],
                "certification_status": "PENDING"
            }
        
        sample_data = {
            "sample_id": result["sample"]["value"].split("#")[-1],
            "pesticide": result["pesticide"]["value"].split("#")[-1],
            "concentration": float(result["value"]["value"])
        }
        
        audit_data["farms"][farm_name]["samples"].append(sample_data)
        
        if "farmType" in result:
            farm_type = result["farmType"]["value"].split("#")[-1]
            audit_data["farms"][farm_name]["certification_status"] = (
                "ORGANIC" if farm_type == "OrganicFarm" else "NON_ORGANIC"
            )
    
    # Save audit trail
    audit_file = os.path.join(REPORTS_DIR, "audit_trail.json")
    with open(audit_file, 'w') as f:
        json.dump(audit_data, f, indent=2)
    
    print(f"📝 Audit trail saved: {audit_file}")
    return audit_data

def main():
    print("📊 Generating compliance reports for organic agriculture certification")
    print("🏛️  Based on EU Regulation 2018/848\n")
    
    # Ensure reports directory exists
    ensure_reports_directory()
    
    try:
        # Generate all reports
        print("1️⃣  Generating compliance report...")
        compliance_summary = generate_compliance_report()
        
        print("\n2️⃣  Generating violation report...")
        violations = generate_violation_report()
        
        print("\n3️⃣  Generating certification report...")
        certifications = generate_certification_report()
        
        print("\n4️⃣  Generating audit trail...")
        audit_data = generate_audit_trail()
        
        # Print summary
        print("\n📈 Report Generation Summary:")
        print(f"   Total Farms Processed: {compliance_summary['total_farms']}")
        print(f"   Organic Certified: {compliance_summary['organic_farms']}")
        print(f"   Non-Organic: {compliance_summary['non_organic_farms']}")
        print(f"   Violations Detected: {len(violations)}")
        print(f"   Certifications Issued: {len(certifications)}")
        
        print(f"\n📁 All reports saved to: {REPORTS_DIR}/")
        print("✅ Report generation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        raise

if __name__ == "__main__":
    main()