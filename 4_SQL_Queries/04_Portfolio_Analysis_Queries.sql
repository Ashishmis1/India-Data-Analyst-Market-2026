SELECT 
    Industry,
    COUNT(jobId) AS Total_Fresher_Jobs,
    ROUND(AVG(CAST(midSalary AS DECIMAL(15,0))), 0) AS Avg_Mid_Salary_INR
FROM 
    job_postings
WHERE 
    CAST(minimumExperience AS UNSIGNED) <= 1
    AND midSalary != '' 
    AND midSalary != '0'
GROUP BY 
    Industry
ORDER BY 
    Total_Fresher_Jobs DESC;