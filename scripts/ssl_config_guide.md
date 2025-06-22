# SSL Configuration Guide for TII API Script

## SSL Issues with TII API

The TII API (`crowdlabel.tii.ae`) has SSL certificate issues that can cause problems when making HTTPS requests. This guide explains the different approaches to handle this.

## Current Configuration

The script currently has SSL verification **disabled by default** to handle the TII API's certificate issues:

```python
# SSL Verification default (SSL verification is disabled by default)
VERIFY_SSL = False
```

## SSL Configuration Options

### 1. **Disabled SSL Verification (Current Default)**
```bash
python3 scripts/pull_TII_all_categories.py --dry-run
```
- **Pros**: Works with problematic certificates
- **Cons**: Less secure, shows warnings
- **Use Case**: Development and testing

### 2. **Enabled SSL Verification**
```bash
python3 scripts/pull_TII_all_categories.py --verify --dry-run
```
- **Pros**: More secure
- **Cons**: May fail with certificate errors
- **Use Case**: Production environments with proper certificates

### 3. **Custom SSL Context (Advanced)**
If you need more control over SSL settings, you can modify the script to use a custom SSL context:

```python
import ssl
import certifi

# Create custom SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Use in requests
response = requests.get(endpoint, headers=headers, verify=ssl_context)
```

## Common SSL Errors and Solutions

### 1. **SSL Certificate Verify Failed**
```
SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed')
```
**Solution**: Use `--verify=False` or don't use the `--verify` flag

### 2. **InsecureRequestWarning**
```
InsecureRequestWarning: Unverified HTTPS request is being made
```
**Solution**: The script already suppresses these warnings with:
```python
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### 3. **Hostname Mismatch**
```
CertificateError: hostname 'crowdlabel.tii.ae' doesn't match
```
**Solution**: Use disabled SSL verification or custom SSL context

## Testing SSL Configuration

### Test with SSL Disabled (Recommended)
```bash
python3 scripts/pull_TII_all_categories.py --dry-run --max-tasks 1
```

### Test with SSL Enabled
```bash
python3 scripts/pull_TII_all_categories.py --verify --dry-run --max-tasks 1
```

### Test with Custom Delay
```bash
python3 scripts/pull_TII_all_categories.py --dry-run --max-tasks 1 --delay 2.0
```

## Production Recommendations

### For Development/Testing
- Use SSL verification disabled (default)
- Monitor for any security implications
- Use `--dry-run` for testing

### For Production
- Contact TII support about certificate issues
- Consider using a proxy or VPN if needed
- Implement proper error handling for SSL failures
- Monitor SSL-related errors

## Troubleshooting

### If SSL Issues Persist
1. Check your network connection
2. Verify the API endpoint is accessible
3. Try with different SSL configurations
4. Contact TII support if the issue is on their end

### Debug SSL Issues
Add debug logging to see SSL details:
```python
import logging
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
```

## Security Considerations

When SSL verification is disabled:
- Data transmission is still encrypted (HTTPS)
- But you can't verify the server's identity
- Man-in-the-middle attacks are theoretically possible
- Consider the security implications for your use case

## Alternative Approaches

### 1. **Use HTTP Instead of HTTPS**
Not recommended as it's less secure, but some APIs support it.

### 2. **Use a Proxy**
Route requests through a trusted proxy with proper certificates.

### 3. **Custom Certificate Bundle**
Provide your own certificate bundle if you have the correct certificates.

## Current Script Behavior

The script is configured to:
- Disable SSL verification by default
- Suppress SSL warnings
- Allow enabling SSL verification with `--verify` flag
- Handle SSL errors gracefully
- Log SSL-related issues for debugging

This configuration balances functionality with security for the current TII API setup. 