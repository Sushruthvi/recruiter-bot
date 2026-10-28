-- Part 2: The SQL Detective Challenge
-- Dataset: sql_detective_data.sql (loaded as given, not redesigned).
-- Written to be portable (no vendor-specific functions); tested on SQLite.
--
-- Assumption used throughout: there is no applications table, so an applicant
-- "applied to" or "reached a stage for" a posting only through their rows in
-- `interviews`.


-- Q1. List all currently open job postings, with the name of the recruiter
--     who owns each one.
--     LEFT JOIN so a posting is never dropped if its recruiter row is missing.
SELECT jp.id AS job_posting_id,
       jp.title,
       jp.department,
       jp.opened_date,
       r.name AS recruiter
  FROM job_postings jp
  LEFT JOIN recruiters r ON r.id = jp.recruiter_id
 WHERE jp.status = 'open'
 ORDER BY jp.id;


-- Q2. For each job posting, how many applicants reached the Final interview
--     stage?
--     "Reached" means having a Final interview scheduled, whatever its outcome.
--     The Final condition sits in the LEFT JOIN's ON clause (not WHERE), so
--     postings with nobody at Final still appear, with 0. People are counted
--     by normalised email, so one person who applied twice is counted once.
SELECT jp.id AS job_posting_id,
       jp.title,
       COUNT(DISTINCT LOWER(TRIM(a.email))) AS applicants_reaching_final
  FROM job_postings jp
  LEFT JOIN interviews i ON i.job_posting_id = jp.id AND i.stage = 'Final'
  LEFT JOIN applicants a ON a.id = i.applicant_id
 GROUP BY jp.id, jp.title
 ORDER BY jp.id;


-- Q3. Find every person who effectively applied to more than one job posting.
--     The data has duplicates: Ananya Rao appears as applicants 1 and 2 with
--     the same email in different letter case. Grouping by applicant id would
--     miss her, so people are identified by lower-cased, trimmed email, and
--     we count the DISTINCT postings across all of their applicant records.
SELECT MIN(a.full_name) AS full_name,
       LOWER(TRIM(a.email)) AS email,
       COUNT(DISTINCT i.job_posting_id) AS postings_applied_to
  FROM applicants a
  JOIN interviews i ON i.applicant_id = a.id
 GROUP BY LOWER(TRIM(a.email))
HAVING COUNT(DISTINCT i.job_posting_id) > 1
 ORDER BY full_name;


-- Q4. For each recruiter, the Final-stage conversion rate
--     (passed / total Final-stage interviews), only for recruiters with at
--     least 3 Final-stage interviews.
--     Pending or failed Finals count in the denominator. The 1.0 * forces
--     decimal division (plain integer division would return 0 or 1).
SELECT r.id AS recruiter_id,
       r.name AS recruiter,
       COUNT(*) AS final_interviews,
       SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS passed,
       ROUND(1.0 * SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2)
           AS conversion_rate
  FROM interviews i
  JOIN job_postings jp ON jp.id = i.job_posting_id
  JOIN recruiters r ON r.id = jp.recruiter_id
 WHERE i.stage = 'Final'
 GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
 ORDER BY conversion_rate DESC, r.id;


-- Q5. (Bonus) Using a window function, the recruiter with the most successful
--     placements (passed at Final stage) in each department.
--     Starting from job_postings with a LEFT JOIN means a department where
--     nobody has a placement yet still shows up, with 0. RANK() keeps ties:
--     recruiters level on placements are all returned for that department.
WITH placements AS (
    SELECT jp.department,
           r.id AS recruiter_id,
           r.name AS recruiter,
           COUNT(i.id) AS placements
      FROM job_postings jp
      JOIN recruiters r ON r.id = jp.recruiter_id
      LEFT JOIN interviews i ON i.job_posting_id = jp.id
                            AND i.stage = 'Final'
                            AND i.outcome = 'passed'
     GROUP BY jp.department, r.id, r.name
),
ranked AS (
    SELECT department, recruiter, placements,
           RANK() OVER (PARTITION BY department ORDER BY placements DESC) AS rnk
      FROM placements
)
SELECT department, recruiter, placements
  FROM ranked
 WHERE rnk = 1
 ORDER BY department, recruiter;
