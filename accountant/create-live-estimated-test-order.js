import { GoogleAuth } from 'google-auth-library';

const SPREADSHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';

async function main() {
  const auth = new GoogleAuth({
    keyFile: './service-account-key.json',
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();

  const timestamp = Date.now().toString().slice(-4);
  const testOrderId = `CJS-WA-${timestamp}`;
  const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 16);

  const row = [
    nowStr,                                // Order Date
    testOrderId,                           // Order ID
    '1001',                                // Customer ID
    'Saniya Boutique',                     // Customer Name
    '+91 9870987978',                      // Phone
    'Machine Embroidery',                  // Order Type
    'Peacock Motif',                       // Template Name
    '1',                                   // Quantity
    '72000',                               // Stitch Count
    '0.5',                                 // Labor Hours
    'Machine 1',                           // Machine
    '2026-09-09',                          // Estimated Delivery Date
    'Rs 1440.0',                           // Estimated Cost
    'Estimated',                           // Payment Status
    'Customer requested 72k stitches peacock embroidery via WhatsApp agent. Routed to Machine 1.', // Reasoning
    ''                                     // Overrides
  ];

  const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/Orders!A1:append?valueInputOption=USER_ENTERED`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ values: [row] })
  });

  const data = await res.json();
  if (!res.ok) {
    console.error('Error:', data.error);
    process.exit(1);
  }

  console.log(`Successfully created live test order: ${testOrderId} in row range: ${data.updates?.updatedRange}`);
}

main();
