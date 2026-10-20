-- Database: MySQL | Author: Ashish Kumar Mishra
-- 1.relational bridge table setup (Star Schema Design)

CREATE TABLE IF NOT EXISTS job_postings (
    jobId BIGINT PRIMARY KEY,
    title VARCHAR(255),
    companyName VARCHAR(255),
    Industry VARCHAR(100),
    Employer_Type VARCHAR(50),
    Role_Track VARCHAR(100),
    Clean_City VARCHAR(100),
    Work_Mode VARCHAR(50),
    tagsAndSkills TEXT,
    minimumExperience INT,
    minimumSalary DECIMAL(15,2) NULL,
    maximumSalary DECIMAL(15,2) NULL,
    midSalary DECIMAL(15,2) NULL,
    Salary_Disclosed VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS bridge_job_skills (
    jobId BIGINT,
    Standardized_Skill VARCHAR(100),
    Role_Track VARCHAR(100),
    minimumExperience INT,
    midSalary DECIMAL(15,2) NULL,
    FOREIGN KEY (jobId) REFERENCES job_postings(jobId)
);


--- 1: Industry Hiring Volume vs Disclosed Salary Benchmarks (in LPA)
SELECT 
    Industry,
    COUNT(jobId) AS Total_Validated_Jobs,
    SUM(CASE WHEN minimumExperience <= 1 THEN 1 ELSE 0 END) AS Fresher_0_to_1_Yr_Jobs,
    COUNT(midSalary) AS Jobs_With_Disclosed_Salary,
    ROUND(AVG(midSalary) / 100000, 2) AS Avg_Salary_LPA,
    ROUND(MAX(midSalary) / 100000, 2) AS Max_Salary_LPA
FROM 
    job_postings
GROUP BY 
    Industry
ORDER BY 
    Total_Validated_Jobs DESC;


-- - 2: Fresher (0-1 Yr) Market Penetration by Role  (Using CTE)
WITH Role_Track_Summary AS (
    SELECT 
        Role_Track,
        COUNT(jobId) AS Total_Openings,
        SUM(CASE WHEN minimumExperience <= 1 THEN 1 ELSE 0 END) AS Fresher_Openings,
        ROUND(AVG(CASE WHEN minimumExperience <= 1 THEN midSalary END) / 100000, 2) AS Fresher_Avg_LPA
    FROM 
        job_postings
    GROUP BY 
        Role_Track
)
SELECT 
    Role_Track,
    Total_Openings,
    Fresher_Openings,
    ROUND((Fresher_Openings * 100.0) / Total_Openings, 1) AS Fresher_Job_Share_Pct,
    Fresher_Avg_LPA
FROM 
    Role_Track_Summary
ORDER BY 
    Fresher_Openings DESC;


------Skill-to-Salary ROI Analysis (Joining Fact Table & Skill Bridge Table)
SELECT 
    s.Standardized_Skill,
    COUNT(DISTINCT s.jobId) AS Total_Jobs_Demanding_Skill,
    SUM(CASE WHEN p.minimumExperience <= 1 THEN 1 ELSE 0 END) AS Fresher_Jobs_Demanding_Skill,
    ROUND(AVG(p.midSalary) / 100000, 2) AS Avg_Skill_Salary_LPA,
    SUM(CASE WHEN p.midSalary >= 1000000 THEN 1 ELSE 0 END) AS Premium_Roles_Above_10LPA
FROM 
    bridge_job_skills s
INNER JOIN 
    job_postings p ON s.jobId = p.jobId
GROUP BY 
    s.Standardized_Skill
ORDER BY 
    Total_Jobs_Demanding_Skill DESC;


-- 
----------- 4: Top 3 Highest-Paying Analyst Roles per Metro Hub (Using Window Function)
WITH Ranked_City_Jobs AS (
    SELECT 
        Clean_City,
        title,
        companyName,
        Role_Track,
        minimumExperience,
        ROUND(midSalary / 100000, 2) AS Salary_LPA,
        DENSE_RANK() OVER (PARTITION BY Clean_City ORDER BY midSalary DESC) AS Salary_Rank
    FROM 
        job_postings
    WHERE 
        midSalary IS NOT NULL
        AND Clean_City IN ('Bangalore', 'Hyderabad', 'Pune', 'Mumbai', 'Gurugram', 'Delhi NCR', 'Chennai')
)
SELECT 
    Clean_City,
    Salary_Rank,
    title,
    companyName,
    Role_Track,
    minimumExperience,
    Salary_LPA
FROM 
    Ranked_City_Jobs
WHERE 
    Salary_Rank <= 3
ORDER BY 
    Clean_City, Salary_Rank;


-- 
------------------ 5: Gold Layer Reporting View for Power BI Dashboard Consumption
CREATE OR REPLACE VIEW vw_gold_analyst_market AS
SELECT 
    jobId,
    title,
    companyName,
    Industry,
    Employer_Type,
    Role_Track,
    Clean_City,
    Work_Mode,
    minimumExperience,
    CASE 
        WHEN minimumExperience <= 1 THEN '0-1 Yrs (Fresher / Entry-Level)'
        WHEN minimumExperience BETWEEN 2 AND 4 THEN '2-4 Yrs (Junior-Mid)'
        WHEN minimumExperience BETWEEN 5 AND 7 THEN '5-7 Yrs (Mid-Senior)'
        ELSE '8+ Yrs (Lead / Principal)'
    END AS Experience_Band,
    ROUND(midSalary / 100000, 2) AS Mid_Salary_LPA,
    Salary_Disclosed,
    CASE 
        WHEN midSalary IS NULL THEN 'Undisclosed'
        WHEN midSalary >= 1000000 THEN 'Premium (>= 10 LPA)'
        WHEN midSalary >= 500000 THEN 'Mid-Tier (5 - 9.9 LPA)'
        ELSE 'Entry-Tier (< 5 LPA)'
    END AS Compensation_Tier
FROM 
    job_postings;