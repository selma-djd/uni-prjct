-- ============================================================
-- Update of an EXISTING database to the new version of the website
-- Run this ONCE in pgAdmin: right-click your database (universitydb)
-- > Query Tool > paste everything > press F5.
-- It is safe to run twice (nothing is duplicated).
-- ============================================================

-- 1) New columns for the departments table
ALTER TABLE departments ADD COLUMN IF NOT EXISTS head         VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS email        VARCHAR(120) NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS programs     TEXT         NOT NULL DEFAULT '';
ALTER TABLE departments DROP COLUMN IF EXISTS laboratories;

-- 2) More details for the 5 existing departments

UPDATE departments SET
    head = E'Prof. Samir Haddad',
    email = E'mathematics@boumerdes-university.example',
    programs = E'Bachelor in Mathematics\nBachelor in Applied Mathematics\nMaster in Probability and Statistics\nMaster in Numerical Analysis'
WHERE name = E'Mathematics' AND head = '';

UPDATE departments SET
    head = E'Prof. Leila Mansouri',
    email = E'physics@boumerdes-university.example',
    programs = E'Bachelor in Physics\nMaster in Condensed Matter Physics\nMaster in Renewable Energy'
WHERE name = E'Physics' AND head = '';

UPDATE departments SET
    head = E'Prof. Yacine Boudiaf',
    email = E'chemistry@boumerdes-university.example',
    programs = E'Bachelor in Chemistry\nMaster in Analytical Chemistry\nMaster in Organic Chemistry'
WHERE name = E'Chemistry' AND head = '';

UPDATE departments SET
    head = E'Prof. Nadia Cherif',
    email = E'biology@boumerdes-university.example',
    programs = E'Bachelor in Biology\nMaster in Microbiology\nMaster in Genetics\nMaster in Ecology'
WHERE name = E'Biology' AND head = '';

UPDATE departments SET
    head = E'Prof. Omar Belkacem',
    email = E'agronomy@boumerdes-university.example',
    programs = E'Bachelor in Agronomy\nMaster in Plant Production\nMaster in Soil Science and Irrigation'
WHERE name = E'Agronomy' AND head = '';


-- 3) The new department: Computer Science
INSERT INTO departments (name, description, details, head, email, programs)
SELECT E'Computer Science',
       E'Programming, algorithms, databases, networks and artificial intelligence.',
       E'The Department of Computer Science teaches programming, algorithms and data structures, databases, computer networks, operating systems and software engineering. Students work on projects in web development, cloud computing and artificial intelligence. The department has computer rooms with Linux workstations and a small server room used for networking and cloud practical work.',
       E'Prof. Rania Slimani',
       E'computer-science@boumerdes-university.example',
       E'Bachelor in Computer Science\nMaster in Software Engineering\nMaster in Artificial Intelligence\nMaster in Networks and Cloud Computing'
WHERE NOT EXISTS (SELECT 1 FROM departments WHERE name = 'Computer Science');

-- 4) Check the result
SELECT id, name, head FROM departments ORDER BY id;
