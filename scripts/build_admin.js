#!/usr/bin/env node
/**
 * Build script for admin.js that injects authorized IPs from environment variables
 * Usage: ADMIN_ALLOWED_IPS="ip1,ip2" node scripts/build_admin.js
 */

const fs = require('fs');
const path = require('path');

const ADMIN_JS_PATH = path.join(__dirname, '../website/admin.js');
const ADMIN_JS_TEMPLATE = path.join(__dirname, '../website/admin.js.template');

// Get IPs from environment variable
const allowedIPs = process.env.ADMIN_ALLOWED_IPS || '';

if (!allowedIPs) {
    console.error('❌ Error: ADMIN_ALLOWED_IPS environment variable not set');
    console.error('   Set it as: ADMIN_ALLOWED_IPS="ip1,ip2,ip3"');
    process.exit(1);
}

// Parse IPs (comma-separated, trim whitespace)
const ipList = allowedIPs
    .split(',')
    .map(ip => ip.trim())
    .filter(ip => ip.length > 0);

if (ipList.length === 0) {
    console.error('❌ Error: No valid IPs found in ADMIN_ALLOWED_IPS');
    process.exit(1);
}

console.log(`📝 Injecting ${ipList.length} authorized IP(s) into admin.js...`);

// Read the admin.js file
let adminJs = fs.readFileSync(ADMIN_JS_PATH, 'utf8');

// Replace the AUTHORIZED_IPS array with the actual IPs
const ipArrayString = ipList.map(ip => `    '${ip}'`).join(',\n');
const replacement = `const AUTHORIZED_IPS = [\n${ipArrayString}\n];`;

// Replace the placeholder
adminJs = adminJs.replace(
    /const AUTHORIZED_IPS = window\.ADMIN_ALLOWED_IPS.*?;[\s\S]*?/,
    replacement
);

// Write the updated file
fs.writeFileSync(ADMIN_JS_PATH, adminJs, 'utf8');

console.log('✅ Admin.js updated with authorized IPs');
console.log(`   IPs: ${ipList.join(', ')}`);
