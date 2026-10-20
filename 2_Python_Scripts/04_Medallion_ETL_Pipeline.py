import pandas as pd
import numpy as np
import re
import os
from datetime import datetime

print("1. Loading Bronze raw dataset...")
raw_path = "1_Raw_Data/bronze_analyst_jobs_raw.csv"
if not os.path.exists(raw_path):
    raw_path = "../1_Raw_Data/bronze_analyst_jobs_raw.csv"

df = pd.read_csv(raw_path)
initial_rows = len(df)
print(f"   Loaded {initial_rows} rows.")

print("2. Removing duplicate job postings and agency spam...")
# Drop exact jobId duplicates first
df = df.drop_duplicates(subset=['jobId'], keep='first')

# Extract Work Mode before cleaning city names
def get_work_mode(row):
    text = f"{row['Clean_City']} {row['title']}".lower()
    if 'remote' in text or 'wfh' in text or 'work from home' in text:
        return 'Remote'
    if 'hybrid' in text:
        return 'Hybrid'
    return 'On-Site'

df['Work_Mode'] = df.apply(get_work_mode, axis=1)

# Clean 'Hybrid - ' and ' Suburban' that were left in Clean_City
df['Clean_City'] = df['Clean_City'].astype(str).str.replace('Hybrid - ', '', case=False)
df['Clean_City'] = df['Clean_City'].str.replace(' Suburban', '', case=False)
df['Clean_City'] = df['Clean_City'].str.replace(' Rural', '', case=False).str.strip()

city_map = {
    'Bengaluru': 'Bangalore', 'Banglore': 'Bangalore', 'Angalore': 'Bangalore',
    'Navi Mumbai': 'Mumbai', 'Thane': 'Mumbai', 'Goregaon': 'Mumbai',
    'Panvel': 'Mumbai', 'Kharghar': 'Mumbai', 'Ulhasnagar': 'Mumbai', 'Dombivli': 'Mumbai',
    'Gurgaon': 'Gurugram', 'Manesar': 'Gurugram', 'Sohna': 'Gurugram',
    'Noida': 'Delhi NCR', 'New Delhi': 'Delhi NCR', 'Delhi': 'Delhi NCR',
    'Faridabad': 'Delhi NCR', 'Ghaziabad': 'Delhi NCR',
    'Secunderabad': 'Hyderabad', 'Pimpri-Chinchwad': 'Pune', 'Tambaram': 'Chennai'
}
df['Clean_City'] = df['Clean_City'].replace(city_map)

# Drop repeated agency spam (same company posting the exact same role & city 20+ times)
df = df.drop_duplicates(subset=['companyName', 'title', 'Clean_City', 'minimumExperience', 'midSalary'], keep='first')
after_dedup_rows = len(df)

print("3. Filtering out non-analytics roles (BPO, Call Audit, Medical Coding, SOC) & classifying tracks...")
def get_role_track(row):
    t = str(row['title']).lower()
    s = str(row['tagsAndSkills']).lower()
    
    # Exclude non-data roles that only matched the word 'Analyst'
    noise_words = [
        'medical cod', 'ar caller', 'ar analyst', 'charge entry', 'call audit',
        'call quality', 'voice process', 'service desk', 'help desk', 'helpdesk',
        'incident', 'soc analyst', 'soc -', 'cyber', 'information security',
        'penetration', 'malware', 'threat', 'security analyst', 'manual tester',
        'automation testing', 'qa analyst', 'quality assurance', 'chemical',
        'genome', 'pharmacovigilance', 'translation', 'graphic designer', 'fea analyst', 'cae analyst'
    ]
    if any(w in t for w in noise_words):
        return 'Exclude'
    if 'quality analyst' in t and any(w in s for w in ['call audit', 'call monitoring', 'bpo', 'selenium', 'manual testing']):
        return 'Exclude'

    # Classify valid roles into clear analytics tracks
    if any(w in t for w in ['data engineer', 'etl', 'snowflake', 'databricks', 'big data']):
        return 'Data Engineering & ETL'
    if any(w in t for w in ['bi ', 'business intelligence', 'power bi', 'tableau', 'mis ', 'reporting analyst']):
        return 'BI & Reporting Analyst'
    if any(w in t for w in ['data analyst', 'data analytics', 'data science', 'decision science', 'quant', 'digital analyst', 'marketing analyst']):
        return 'Data Analyst'
    if any(w in t for w in ['business analyst', 'product analyst', 'business system', 'strategy', 'functional analyst']):
        return 'Business & Product Analyst'
    if any(w in t for w in ['financial', 'finance', 'credit', 'risk', 'pricing', 'treasury', 'valuation', 'equity', 'investment', 'revenue', 'tax', 'audit', 'kyc', 'aml', 'fraud']):
        return 'Financial & Risk Analyst'
    if any(w in s for w in ['sql', 'power bi', 'tableau', 'python', 'data analysis', 'advanced excel', 'vlookup', 'pivot table']):
        return 'Operations & General Analyst'
    return 'Exclude'

df['Role_Track'] = df.apply(get_role_track, axis=1)
noise_removed = len(df[df['Role_Track'] == 'Exclude'])
df = df[df['Role_Track'] != 'Exclude'].copy()

print("4. Fixing Industry classification (Fixing American Express & Manpower bugs)...")
def get_industry_v3(row):
    c = str(row['companyName']).lower()
    s = str(row['tagsAndSkills']).lower()
    
    # 1. Check Company Name first (Staffing checked before Manufacturing so 'Manpower' != 'Power')
    if any(x in c for x in ['staffing', 'manpower', 'recruitment', 'consultancy', 'hr solutions', 'hr services', 'hr consulting', 'placement', 'talent', 'adecco', 'randstad', 'quess', 'teamlease', 'persolkelly', 'kelly', 'nlb services', 'ciel hr', 'lancesoft', 'artech', 'crescendo', 'uplers', 'white horse', 'rivera', 'gratitude india', 'job factory', 'career next', 'hiresquad', 'job world', 'venpa', 'huntingcube', 'genius consultants']):
        return 'Staffing/HR Services'
    if any(x in c for x in ['american express', 'amex', 'bank', 'finance', 'financial', 'capital', 'insurance', 'finserv', 'hdfc', 'icici', 'kotak', 'axis', 'sbi', 'bajaj', 'nbfc', 'credit', 'wealth', 'trading', 'securities', 'jpmorgan', 'goldman sachs', 'morgan stanley', 'barclays', 'hsbc', 'nomura', 'crisil', 'morningstar', 'invesco', 'visa', 'swiss re', 'fidelity', 'bny', 'dtcc', 'fis', 'moodys', 's&p global', 'ameriprise', 'payu', 'fampay', 'coindcx', 'indusind', 'wells fargo', 'societe generale', 'broadridge', 'allstate', 'axa', 'mufg']):
        return 'BFSI'
    if any(x in c for x in ['consulting', 'consult', 'mckinsey', 'bcg', 'bain', 'kpmg', 'pwc', 'ey', 'ernst', 'deloitte', 'grant thornton', 'oliver wyman', 'guidehouse', 'evalueserve', 'tresvista', 'eclerx', 'exl', 'genpact', 'mercer', 'axtria', 'gartner', 'annalect', 'audit', 'tax']):
        return 'Consulting'
    if any(x in c for x in ['flipkart', 'myntra', 'retail', 'ecommerce', 'swiggy', 'zomato', 'meesho', 'nykaa', 'bigbasket', 'deliveroo', 'redbus', 'purplle', 'olx', 'cardekho', 'fedex', 'ups supply', 'maersk', 'world courier', 'booking holdings', 'delivery', 'logistics']):
        return 'Ecommerce/Logistics'
    if any(x in c for x in ['pharma', 'health', 'medical', 'hospital', 'apollo', 'fortis', 'cipla', 'sun pharma', 'dr reddy', 'biotech', 'life sciences', 'cigna', 'optum', 'amgen', 'iqvia', 'syneos', 'bristol myers', 'roche', 'stryker', 'boston scientific', 'alcon', 'certara', 'eurofins', 'r1 rcm', 'intas']):
        return 'Healthcare'
    if any(x in c for x in ['tata', 'reliance', 'mahindra', 'larsen', 'l&t', 'steel', 'power', 'energy', 'jindal', 'adani', 'auto', 'motors', 'bosch', 'siemens', 'vedanta', 'maruti', 'caterpillar', 'ford', 'abb', 'chevron', 'lubrizol', 'flex', 'diageo', 'general mills', 'construction', 'engineering']):
        return 'Manufacturing/Core'
    if any(x in c for x in ['tech', 'software', 'solutions', 'systems', 'info', 'wipro', 'infosys', 'tcs', 'hcl', 'cognizant', 'accenture', 'capgemini', 'mphasis', 'lti', 'ibm', 'microsoft', 'google', 'amazon', 'data', 'analytics', 'cloud', 'digital', 'oracle', 'sap', 'workday', 'zendesk', 'reuters']):
        return 'IT/Tech'
        
    # 2. Fallback: Check skill tags if company name didn't match so 'Other' stays small
    if any(x in s for x in ['investment banking', 'credit risk', 'underwriting', 'aml', 'kyc', 'us gaap', 'capital market', 'hedge funds', 'reinsurance', 'mortgage']):
        return 'BFSI'
    if any(x in s for x in ['clinical', 'pharma', 'healthcare', 'hipaa', 'medical']):
        return 'Healthcare'
    if any(x in s for x in ['supply chain', 'procurement', 'inventory', 'logistics', 'warehouse', 'ecommerce']):
        return 'Ecommerce/Logistics'
    if any(x in s for x in ['sql', 'python', 'power bi', 'tableau', 'snowflake', 'azure', 'aws', 'etl', 'software', 'agile', 'jira', 'sap', 'erp']):
        return 'IT/Tech'
    return 'Other'

df['Industry'] = df.apply(get_industry_v3, axis=1)
df['Employer_Type'] = df['Industry'].apply(lambda x: 'Recruitment Agency' if x == 'Staffing/HR Services' else 'Direct Employer')

print("5. Extracting hidden salary bands using Regex & cleaning salary anomalies...")
df['minimumSalary'] = pd.to_numeric(df['minimumSalary'], errors='coerce').fillna(0)
df['maximumSalary'] = pd.to_numeric(df['maximumSalary'], errors='coerce').fillna(0)
df['midSalary'] = pd.to_numeric(df['midSalary'], errors='coerce').fillna(0)
df['minimumExperience'] = pd.to_numeric(df['minimumExperience'], errors='coerce').fillna(0).astype(int)

# Regex function to extract LPA salaries written inside job titles (e.g., "7lpa", "5.5 L", "6 LPA")
def extract_title_salary_lpa(title):
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lpa|lacs?|lakhs?|l\b)', str(title), re.IGNORECASE)
    if match:
        val = float(match.group(1))
        if 1.0 <= val <= 80.0:
            return val * 100000
    return None

regex_matches = 0
for idx, row in df.iterrows():
    extracted_sal = extract_title_salary_lpa(row['title'])
    if extracted_sal is not None:
        regex_matches += 1
        if row['midSalary'] <= 0:
            df.at[idx, 'minimumSalary'] = extracted_sal
            df.at[idx, 'maximumSalary'] = extracted_sal
            df.at[idx, 'midSalary'] = extracted_sal

# Clean invalid salaries (< 1 Lakh/year are monthly stipends or data errors) and set undisclosed (0) to NaN
df.loc[df['midSalary'] < 100000, ['minimumSalary', 'maximumSalary', 'midSalary']] = np.nan
df['Salary_Disclosed'] = df['midSalary'].notna().map({True: 'Yes', False: 'No'})

# Save audit log for Data Engineering tracking
out_dir = "3_Cleaned_Data" if os.path.exists("3_Cleaned_Data") else "../3_Cleaned_Data"
audit_df = pd.DataFrame([{
    'Run_Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
    'Raw_Analyst_Rows': initial_rows,
    'Duplicates_Removed': initial_rows - after_dedup_rows,
    'Non_Analytics_Noise_Removed': noise_removed,
    'Regex_Salary_Matches': regex_matches,
    'Final_Valid_Jobs': len(df),
    'Disclosed_Salary_Jobs': int(df['midSalary'].notna().sum())
}])
audit_df.to_csv(f"{out_dir}/ETL_Pipeline_Audit_Log.csv", index=False)

print("6. Building Normalized Skill-Bridge Table & Exporting Gold Layer CSVs...")
skill_map = {
    'SQL': ['sql', 'mysql', 'postgresql', 't-sql', 'plsql', 'pl-sql', 'sql server', 'ms sql', 'rdbms'],
    'Excel': ['excel', 'advanced excel', 'vlookup', 'pivot table', 'macros', 'vba', 'power query', 'spreadsheets', 'google sheets'],
    'Python': ['python', 'pandas', 'numpy', 'pyspark', 'scikit-learn', 'matplotlib'],
    'Power BI': ['power bi', 'powerbi', 'dax', 'ssrs', 'ssas', 'power platform'],
    'Tableau': ['tableau', 'looker', 'qlikview', 'domo', 'spotfire', 'google data studio'],
    'ETL & Data Warehousing': ['etl', 'data warehousing', 'data modeling', 'ssis', 'informatica', 'alteryx', 'talend', 'data pipeline', 'star schema'],
    'Cloud & Lakehouse': ['aws', 'azure', 'gcp', 'snowflake', 'databricks', 'bigquery', 'hive', 'spark', 'cloud'],
    'R / SAS / SPSS': [' sas', 'sas,', 'r programming', 'spss'],
    'Statistics & ML': ['statistics', 'statistical', 'machine learning', 'predictive', 'forecasting', 'regression', 'hypothesis testing'],
    'Business Analysis & Agile': ['business analysis', 'requirement gathering', 'brd', 'frd', 'uat', 'agile', 'scrum', 'jira', 'visio', 'stakeholder management'],
    'Financial & Risk Modeling': ['financial analysis', 'financial modelling', 'financial reporting', 'budgeting', 'variance analysis', 'credit risk', 'risk management', 'valuation', 'us gaap'],
    'ERP & CRM (SAP/Salesforce)': ['sap', 'erp', 'salesforce', 'oracle', 'netsuite', 'sfdc', 'crm'],
    'Web & Digital Analytics': ['google analytics', 'adobe analytics', 'mixpanel', 'seo', 'google ads', 'digital marketing']
}

skill_rows = []
for idx, row in df.iterrows():
    raw_skills = str(row['tagsAndSkills']).lower()
    for clean_skill, keywords in skill_map.items():
        if any(k in raw_skills for k in keywords):
            skill_rows.append({
                'jobId': row['jobId'],
                'Standardized_Skill': clean_skill,
                'Role_Track': row['Role_Track'],
                'minimumExperience': row['minimumExperience'],
                'midSalary': row['midSalary']
            })

df_skills_bridge = pd.DataFrame(skill_rows)

# Export Gold Layer Files into 3_Cleaned_Data
df.to_csv(f"{out_dir}/Master_Analyst_Data_Cleaned.csv", index=False)
df_fresher = df[df['minimumExperience'] <= 1].copy()
df_fresher.to_csv(f"{out_dir}/Excel_Analysis_Sample.csv", index=False)
df_skills_bridge.to_csv(f"{out_dir}/Gold_Bridge_Job_Skills.csv", index=False)

# Update Top 100 Fresher Jobs extract with clean, validated fresher roles
df_top100_fresher = df_fresher[df_fresher['midSalary'].notna()].sort_values(by='midSalary', ascending=False).head(100)
df_top100_fresher.to_csv(f"{out_dir}/Top_100_Fresher_Jobs_Excel_Extract.csv", index=False)

print("\n" + "="*40)
print("✅ MEDALLION ETL PIPELINE COMPLETE!")
print(f"Final Validated Analyst Jobs: {len(df)} (Fresher 0-1 Yr Jobs: {len(df_fresher)})")
print(f"Total Skill Mappings Extracted: {len(df_skills_bridge)}")
print("\n--- Updated Industry Distribution ---")
print(df['Industry'].value_counts())
print("\n--- Top Demanded Skills (Bridge Table) ---")
print(df_skills_bridge['Standardized_Skill'].value_counts().head(10))
print("="*40)